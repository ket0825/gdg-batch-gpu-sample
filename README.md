# GCP Batch Job with GPU in Multiple Regions example

*Read this in other languages: [한국어](docs/README_ko.md)*


### Prerequisites
1. Create a default VPC network (IF YOU WANT TO USE WITH YOUR OWN VPC, USE VPC PEERING WITH DEFAULT VPC or USE NAT GATEWAY)
    
    **TIP**
    > Use the default VPC network for simplicity

2. Set up service account and permissions (API activation required in console)

    **TIP**
    > Enable VPC, Compute Engine, and Batch API in the console.


3. Check and configure GPU Quota (GPU Quota must be set up per region if not available)
    
    **NOTE**   
   > GPU Quota can only be configured 2 days after project creation

4. Check gcloud SDK installation


### Instructions

1. Build and push Docker image
    ```bash
    docker build -t [DOCKER_USERNAME]/batch-gpu .

    docker push [DOCKER_USERNAME]/batch-gpu
    ```

2. Create Global Instance template (using console or gcloud command. Example below)
    ```bash
    gcloud compute instance-templates create-with-container it-batch-gpu-sample \
    --project=[PROJECT_NAME] \
    --machine-type=n1-standard-2 \
    --network-interface=network=default,network-tier=PREMIUM,stack-type=IPV4_ONLY \
    --no-restart-on-failure \
    --maintenance-policy=TERMINATE \
    --provisioning-model=SPOT \
    --instance-termination-action=STOP \
    --service-account=[SERVICE_ACCOUNT] \
    --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/trace.append \
    --accelerator=count=1,type=nvidia-tesla-t4 \
    --tags=http-server,https-server,lb-health-check \
    --container-image=[CONTAINER_URI] \
    --container-restart-policy=always \
    --create-disk=auto-delete=yes,boot=yes,device-name=it-batch-gpu-sample,image=projects/cos-cloud/global/images/cos-stable-117-18613-75-72,mode=rw,size=50,type=pd-balanced \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=container-vm=cos-stable-117-18613-75-72 \  
    ```

3. Set up environment variables and run batch-sample.py to verify batch job creation (MODIFY THE ENVIRONMENT VARIABLES IN THE SCRIPT)

    ```python
    python3 -m venv .

    source bin/activate

    pip3 install -r requirements.txt

    python3 batch-sample.py
    ```






