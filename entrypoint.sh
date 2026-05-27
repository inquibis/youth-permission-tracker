#!/bin/sh
# Entrypoint script to inject environment variables into static files

# Set defaults if not provided
API_BASE_URL=${API_BASE_URL:-http://localhost:8000}
BASE_URL=${BASE_URL:-http://localhost:8000}
API_BASE=${API_BASE:-http://localhost:8000}
WEB_BASE_URL=${WEB_BASE_URL:-http://brookhurst.centervillenorthstake.com}

# Export variables so envsubst can access them
export API_BASE_URL
export BASE_URL
export API_BASE
export WEB_BASE_URL

# Find all HTML files and process them with envsubst
find /usr/share/nginx/html -name "*.html" -type f | while read file; do
  # Create temporary file
  temp_file="${file}.tmp"
  
  # Replace template variables with actual environment values
  envsubst < "$file" > "$temp_file"
  
  # Move temp file back to original
  mv "$temp_file" "$file"
done

# Start nginx
exec nginx -g "daemon off;"
