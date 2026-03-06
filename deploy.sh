# This script is used to deploy the latest version of Voyage to the server. It pulls the latest version of the Docker images and starts the containers. It is a simple script that can be run on the server, possibly as a cron job, to keep the server up to date with the latest version of the application.

echo "Deploying latest version of Voyage"
docker compose pull
echo "Stating containers"
docker compose up -d
echo "All set!"
docker logs voyage-backend --follow