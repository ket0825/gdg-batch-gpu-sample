## GCP Batch Job with GPU in Multiple Regions example

### Prerequisites
1. 기본 VPC 네트워크 생성 (default)
2. 서비스 계정 및 권한 설정 (콘솔에서 API 사용 허가 필요)
   ```bash
   VPC, Compute Engine, Batch API 콘솔에서 사용 허가하기
   ```
3. GPU Quota 확인 및 설정 (GPU Quota가 없으면 리전별로 설정해야 함)
   ```bash
   주의! GPU Quota는 프로젝트 생성 이후 2일 이후에 설정 가능
   ```
4. gcloud sdk 설치 필요.


### Instructions

1. 도커 이미지 빌드 및 푸시
    ```bash
    docker build -t [DOCKER_USERNAME]/batch-gpu .

    docker push [DOCKER_USERNAME]/batch-gpu
    ```

2. Global Instance template 생성 (콘솔 혹은 gcloud 명령어 사용. 아래는 예시이니 변할 수 있습니다.)
    ```bash
    gcloud compute instance-templates create-with-container it-batch-gpu-sample \
    --project=[프로젝트명] \
    --machine-type=n1-standard-2 \
    --network-interface=network=default,network-tier=PREMIUM,stack-type=IPV4_ONLY \
    --no-restart-on-failure \
    --maintenance-policy=TERMINATE \
    --provisioning-model=SPOT \
    --instance-termination-action=STOP \
    --service-account=[서비스계정] \
    --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/trace.append \
    --accelerator=count=1,type=nvidia-tesla-t4 \
    --tags=http-server,https-server,lb-health-check \
    --container-image=[컨테이너 uri] \
    --container-restart-policy=always \
    --create-disk=auto-delete=yes,boot=yes,device-name=it-batch-gpu-sample,image=projects/cos-cloud/global/images/cos-stable-117-18613-75-72,mode=rw,size=50,type=pd-balanced \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=container-vm=cos-stable-117-18613-75-72 \    
    ```

3. 환경변수 설정 이후 batch-sample.py 실행하여 batch job 생성이 잘 되는지 확인 (스크립트 내 환경변수 수정 필요)

    ```python
    python3 -m venv .

    source bin/activate

    pip3 install -r requirements.txt

    python3 batch-sample.py
    ```






