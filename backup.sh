# This script will create a backup of the voyage_media volume and store it in the current directory as voyage-backup.tar.gz

docker run --rm \
  -v voyage_voyage_media:/backup-volume \
  -v "$(pwd)":/backup \
  busybox \
  tar -zcvf /backup/voyage-backup.tar.gz /backup-volume