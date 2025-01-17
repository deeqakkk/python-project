from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from typing import List
from app.database import Database
from app.models import UserCreate, UserInDB, RoleInDB, PermissionInDB, UserRole
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user

db = Database()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(lifespan=lifespan, title="RBAC System")

# Authentication endpoints
@app.post("/auth/login")
async def login(username: str, password: str):
    query = """
    SELECT id, username, hashed_password 
    FROM users 
    WHERE username = $1
    """
    user = await db.fetch_one(query, username)
    
    if not user or not verify_password(password, user['hashed_password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": str(user['id'])})
    return {"access_token": access_token, "token_type": "bearer"}

# User endpoints
@app.post("/users", response_model=UserInDB)
async def create_user(user: UserCreate):
    query = """
    INSERT INTO users (username, email, hashed_password, is_active)
    VALUES ($1, $2, $3, $4)
    RETURNING id, username, email, is_active, created_at
    """
    
    hashed_password = get_password_hash(user.password)
    try:
        # Modified to explicitly return all required fields
        record = await db.fetch_one(
            query, 
            user.username, 
            user.email, 
            hashed_password,
            True  # is_active default value
        )

        if user.username.lower() == "admin":
            query_role = """
            INSERT INTO user_roles (user_id, role_id)
            SELECT $1, id FROM roles WHERE name = 'admin'
            ON CONFLICT (user_id, role_id) DO NOTHING
            """
            await db.execute(query_role, record["id"])
        
        # Convert Record to dict and create UserInDB instance
        user_data = {
            "id": record["id"],
            "username": record["username"],
            "email": record["email"],
            "is_active": record["is_active"],
            "created_at": record["created_at"]
        }
        return UserInDB(**user_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users", response_model=List[UserInDB])
async def get_users(current_user: int = Depends(get_current_user)):
    query = """
    SELECT id, username, email, is_active, created_at
    FROM users
    """
    records = await db.fetch_all(query)
    return [UserInDB(**dict(record)) for record in records]

@app.get("/users/{user_id}", response_model=UserInDB)
async def get_user(user_id: int, current_user: int = Depends(get_current_user)):
    query = """
    SELECT id, username, email, is_active, created_at
    FROM users
    WHERE id = $1
    """
    record = await db.fetch_one(query, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="User not found")
    return UserInDB(**dict(record))

# Role endpoints
@app.post("/roles/{role_name}/users/{user_id}")
async def assign_role_to_user(
    role_name: UserRole,
    user_id: int,
    current_user: int = Depends(get_current_user)
):
    # First, check if the current user has admin role
    admin_check_query = """
    SELECT EXISTS (
        SELECT 1
        FROM users u
        JOIN user_roles ur ON u.id = ur.user_id
        JOIN roles r ON ur.role_id = r.id
        WHERE u.id = $1 AND r.name = 'admin'
    ) as is_admin
    """
    
    result = await db.fetch_one(admin_check_query, current_user)
    if not result or not result['is_admin']:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Then proceed with role assignment
    assign_query = """
    WITH role_id AS (
        SELECT id FROM roles WHERE name = $1
    )
    INSERT INTO user_roles (user_id, role_id)
    SELECT $2, id FROM role_id
    ON CONFLICT (user_id, role_id) DO NOTHING
    RETURNING user_id
    """
    
    try:
        result = await db.fetch_one(assign_query, role_name, user_id)
        if result:
            return {"message": "Role assigned successfully"}
        else:
            raise HTTPException(status_code=400, detail="Role assignment failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Add this function to help with permission checking
async def is_admin(user_id: int, db) -> bool:
    query = """
    SELECT EXISTS (
        SELECT 1
        FROM users u
        JOIN user_roles ur ON u.id = ur.user_id
        JOIN roles r ON ur.role_id = r.id
        WHERE u.id = $1 AND r.name = 'admin'
    ) as is_admin
    """
    result = await db.fetch_one(query, user_id)
    return result['is_admin'] if result else False

# Updated permission checking function
async def check_user_permission(user_id: int, resource: str, action: str) -> bool:
    # First check if user is admin
    is_admin_user = await is_admin(user_id, db)
    if is_admin_user:
        return True
        
    # If not admin, check specific permissions
    query = """
    SELECT EXISTS (
        SELECT 1
        FROM users u
        JOIN user_roles ur ON u.id = ur.user_id
        JOIN role_permissions rp ON ur.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE u.id = $1 AND p.resource = $2 AND p.action = $3
    ) as has_permission
    """ 
    result = await db.fetch_one(query, user_id, resource, action)
    return result['has_permission'] if result else False

@app.get("/roles", response_model=List[RoleInDB])
async def get_roles(current_user: int = Depends(get_current_user)):
    has_access = await check_user_permission(current_user, "roles", "read")
    if not has_access:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    query = "SELECT id, name, description, created_at FROM roles"
    return await db.fetch_all(query)

# Permission endpoints
@app.post("/permissions")
async def create_permission(
    name: str,
    resource: str,
    action: str,
    current_user: int = Depends(get_current_user)
):
    has_access = await check_user_permission(current_user, "permissions", "create")
    if not has_access:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    query = """
    INSERT INTO permissions (name, resource, action)
    VALUES ($1, $2, $3)
    RETURNING id, name, resource, action, created_at
    """
    result = await db.fetch_one(query, name, resource, action)
    return PermissionInDB(**dict(result))

@app.get("/permissions", response_model=List[PermissionInDB])
async def get_permissions(current_user: int = Depends(get_current_user)):
    has_access = await check_user_permission(current_user, "permissions", "read")
    if not has_access:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    query = "SELECT id, name, resource, action, description, created_at FROM permissions"
    result = await db.fetch_all(query)
    return [PermissionInDB(**dict(record)) for record in result]


@app.get("/validate-access/{resource}/{action}")
async def validate_access(
    resource: str,
    action: str,
    current_user: int = Depends(get_current_user)
):
    has_access = await check_user_permission(current_user, resource, action)
    
    # Log the access attempt
    query = """
    INSERT INTO audit_logs (user_id, action, resource, outcome)
    VALUES ($1, $2, $3, $4)
    """
    await db.execute(
        query,
        current_user,
        action,
        resource,
        "granted" if has_access else "denied"
    )
    
    return {"access": has_access}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)