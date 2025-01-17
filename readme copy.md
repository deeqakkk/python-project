### .env file
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
SECRET_KEY=rbac_system

## how to run?
```
python3.11 -m venv env
source env/bin/activate

pip install -r requirements.txt
python migrate.py

run `uvicorn main:app --host 0.0.0.0 --port 8000` or `main.py` directly
```

# Store the API base URL
BASE_URL="http://localhost:8000"

# 1. Create Admin User
echo "Creating admin user..."
curl -X POST "${BASE_URL}/users" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "Admin123!"
  }'

# 2. Login as Admin
echo "\n\nLogging in as admin..."
TOKEN=$(curl -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/form-data" \
  -d "username=admin&password=Admin123!" | jq -r '.access_token')

echo "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzM3MTA3MTg1fQ.xw45we0qRiyxutlB2UjWXOOsHFtXirpXse1kjK_X2FE"

# 3. Create Regular User
echo "\n\nCreating regular user..."
curl -X POST "${BASE_URL}/users" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "staff1",
    "email": "staff1@example.com",
    "password": "Staff123!"
  }'

# 4. List all users (requires admin access)
echo "\n\nListing all users..."
curl -X GET "${BASE_URL}/users" \
  -H "Authorization: Bearer $TOKEN"

# 5. Assign admin role to admin user
echo "\n\nAssigning admin role..."
curl -X POST "${BASE_URL}/roles/admin/users/1" \
  -H "Authorization: Bearer $TOKEN"

# 6. Create permissions for different resources
echo "\n\nCreating permissions..."
# Users management permission
curl -X POST "${BASE_URL}/permissions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "manage_users",
    "resource": "users",
    "action": "manage"
  }'

# Roles management permission
curl -X POST "${BASE_URL}/permissions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "manage_roles",
    "resource": "roles",
    "action": "manage"
  }'

# 7. List all permissions
echo "\n\nListing all permissions..."
curl -X GET "${BASE_URL}/permissions" \
  -H "Authorization: Bearer $TOKEN"

# 8. List all roles
echo "\n\nListing all roles..."
curl -X GET "${BASE_URL}/roles" \
  -H "Authorization: Bearer $TOKEN"

# 9. Assign staff role to regular user
echo "\n\nAssigning staff role to regular user..."
curl -X POST "${BASE_URL}/roles/staff/users/2" \
  -H "Authorization: Bearer $TOKEN"

# 10. Validate access for admin user
echo "\n\nValidating admin access to users resource..."
curl -X GET "${BASE_URL}/validate-access/users/manage" \
  -H "Authorization: Bearer $TOKEN"

# 11. Login as regular user
echo "\n\nLogging in as regular user..."
STAFF_TOKEN=$(curl -X POST "${BASE_URL}/auth/login" \
  -d "username=staff1&password=Staff123!" | jq -r '.access_token')

echo "Staff Token: $STAFF_TOKEN"

# 12. Try to access admin resources with staff user (should be denied)
echo "\n\nTrying to access admin resources with staff user..."
curl -X GET "${BASE_URL}/users" \
  -H "Authorization: Bearer $STAFF_TOKEN"

# 13. Check audit logs (admin only)
echo "\n\nChecking audit logs..."
curl -X GET "${BASE_URL}/audit-logs?hours=24" \
  -H "Authorization: Bearer $TOKEN"

# Example of validating specific permissions
echo "\n\nValidating specific permissions..."
RESOURCES=("users" "roles" "permissions" "audit_logs")
ACTIONS=("read" "create" "update" "delete")

for resource in "${RESOURCES[@]}"; do
  for action in "${ACTIONS[@]}"; do
    echo "\nChecking $action permission on $resource..."
    curl -X GET "${BASE_URL}/validate-access/$resource/$action" \
      -H "Authorization: Bearer $TOKEN"
  done
done