#!/bin/sh
set -e

echo "🚀 Starting Payment Processing System..."

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
until pg_isready -h db -p 5432 -U postgres > /dev/null 2>&1; do
  echo "   Database not ready, waiting 2 seconds..."
  sleep 2
done
echo "✅ Database is ready!"

# Run database migrations
echo "🔄 Running database migrations..."
alembic upgrade head || echo "⚠️  Note: Migrations may have failed or are already applied"

# Start the application
echo "🌟 Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
