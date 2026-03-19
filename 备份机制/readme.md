## step1 源服务器上生成密钥拷贝到备份服务器
~~~bash
ssh-keygen -t rsa -b 4096
ssh-copy-id backup@192.168.**.**
~~~

## step2 显式备份原本本地化的postgresql数据库（不必做）

原本的sql文件虽然做了docker本地化，但是不够显式，不方便备份，将其拷贝到./pg_data，采用本地化指定目录挂载的方式更方便备份。本次做完后，后续无需此步骤

~~~bash
(pytorch) /path/to/proj$ docker volume inspect wind_whisper_rag_system-debug_postgres_data
[
    {
        "CreatedAt": "2025-09-23T09:27:57+08:00",
        "Driver": "local",
        "Labels": {
            "com.docker.compose.project": "wind_whisper_rag_system-debug",
            "com.docker.compose.version": "2.21.0",
            "com.docker.compose.volume": "postgres_data"
        },
        "Mountpoint": "/var/lib/docker/volumes/wind_whisper_rag_system-debug_postgres_data/_data",
        "Name": "wind_whisper_rag_system-debug_postgres_data",
        "Options": null,
        "Scope": "local"
    }
]
sudo cp -a /var/lib/docker/volumes/wind_whisper_rag_system-debug_postgres_data/_data ./pg_data

sudo cp -a $SOURCE_PATH ./pg_data
# 将文件夹及其内容的所有者改为 UID 999 (postgres)
sudo chown -R 101:104 ./pg_data
sudo chmod 700 ./pg_data
~~~

## step3 rsync增量备份

~~~python
'''
while True:
    逻辑判断此刻距离零点还有N时间;
    等待N时间+10min后，执行./remote_sync_backup.sh(stop 容器；备份文件夹；启动容器)
'''
sudo nohup python3 ./备份机制/backup_rsync.py > ./logs/backup_rsync.log &
~~~



