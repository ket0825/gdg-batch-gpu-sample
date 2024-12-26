## GCP Batch Job with GPU in Multiple Regions example

### Instructions

1. 도커 이미지 빌드 및 푸시
    ```bash
    docker build -t [DOCKER_USERNAME]/batch-gpu .

    docker push [DOCKER_USERNAME]/batch-gpu
    ```

2. Global Instance template 생성 (콘솔 혹은 gcloud 명령어 사용. 아래는 예시입니다.)
    ```bash
    gcloud compute instance-templates create-with-container batch-gpu-template \
    --machine-type n1-standard-2 \
    --accelerator type=nvidia-tesla-t4,count=1 \
    --container-image [DOCKER_USERNAME]/batch-gpu \
    --container-restart-policy always \
    --container-stdin \
    --container-tty \
    --container-mount-host-path mount-path=/mnt/data,host-path=/mnt/data,mode=rw \
    --container-env-file .env
    ```

3. 환경변수 설정 이후 batch-sample.py 실행하여 batch job 생성이 잘 되는지 확인

    ```python

    python3 -m venv .

    source bin/activate

    pip install -r requirements.txt
    ```






