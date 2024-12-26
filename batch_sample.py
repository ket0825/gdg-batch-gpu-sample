# MARK: 반드시 디렉토리 변경 후에 코드 실행 (.env).
import os
from copy import deepcopy
import time
from typing import List

# from dotenv import load_dotenv
from google.cloud import batch_v1
from google.api_core import retry
from google.api_core import timeout as timeout_
from google.cloud import compute_v1

# load_dotenv()
REPOSITORY = os.getenv('REPOSITORY', "default")
IMAGE_NAME = os.getenv('IMAGE_NAME', "default")
TAG = os.getenv('TAG', "default")
VPC_NAME = os.getenv('VPC_NAME', "default")
PROJECT_ID = os.getenv('PROJECT_ID', "default")
ZONES = os.getenv('ZONES', "northamerica-northeast1-c,southamerica-east1-a,southamerica-east1-c,us-central1-a,us-central1-b,us-central1-c,us-central1-f,us-east1-c,us-east1-d,us-east4-a,us-east4-b,us-east4-c,us-west1-a,us-west1-b,us-west2-b,us-west2-c,us-west3-b,us-west4-a,us-west4-b")

# 커스텀 재시도 정책 정의 (재시도 없음)
no_retry = retry.Retry(
    predicate=retry.if_exception_type(),  # 빈 predicate = 재시도 안 함
    initial=1.0,
    maximum=5.0,
    multiplier=1.5,
    deadline=60.0  # 전체 시도 시간 제한 (초)
)

# timeout 설정
timeout = timeout_.ConstantTimeout(60.0)  # 30초

def get_instance_template(client: compute_v1.InstanceTemplatesClient, project_id: str, template_name: str) -> compute_v1.InstanceTemplate:
    """기존 instance template을 가져옵니다."""
    return client.get(project=project_id, instance_template=template_name)

def create_modified_template(
    project_id: str, 
    source_template_name: str,
    new_template_name: str,
    new_subnet: str,
    new_region: str,    
    env_vars: dict
) -> compute_v1.Operation:
    """
    기존 template을 복제하고 subnet과 region을 변경합니다.
    
    Args:
        project_id: GCP 프로젝트 ID
        source_template_name: 복제할 원본 템플릿 이름
        new_template_name: 새로 생성할 템플릿 이름
        new_subnet: 새로운 서브넷 (형식: projects/PROJECT/regions/REGION/subnetworks/SUBNET)
        new_region: 새로운 리전 (예: us-central1)
    """
    client = compute_v1.InstanceTemplatesClient()
    
    # 원본 템플릿 가져오기
    source_template = get_instance_template(client, project_id, source_template_name)
    
    # 새로운 템플릿 객체 생성
    new_template = compute_v1.InstanceTemplate()    
    
    # 원본 템플릿의 속성을 복사
    template_copy = deepcopy(source_template)
    
    # name 필드 제거 (API에서 자동 거부됨)
    if hasattr(template_copy, 'name'):
        delattr(template_copy, 'name')
    
    # 기타 자동 생성 필드 제거
    if hasattr(template_copy, 'id'):
        delattr(template_copy, 'id')
    if hasattr(template_copy, 'creation_timestamp'):
        delattr(template_copy, 'creation_timestamp')
    if hasattr(template_copy, 'self_link'):
        delattr(template_copy, 'self_link')
    
    # 새로운 템플릿에 복사한 속성 할당
    new_template = template_copy
    
    # 템플릿 이름 변경
    new_template.name = new_template_name
    new_template.description = f"Cloned from {source_template_name} with modified subnet and region"
    # 네트워크 인터페이스 region 변경        
    new_template.region = new_region        
            
    # 네트워크 인터페이스 region 및 subnet 변경: 
    if new_template.properties.network_interfaces:                
        new_template.properties.network_interfaces[0].subnetwork = new_subnet
        
    # MARK: region 관련 설정 변경 (예: disk source image): 미사용...
    if new_template.properties.disks:
        for disk in new_template.properties.disks:
            if disk.source and 'regions' in disk.source:
                disk.source = disk.source.replace(
                    disk.source.split('/regions/')[1].split('/')[0],
                    new_region
                )
    
    # MARK: SPOT 인스턴스 사용 안하는 경우.                
    # new_template.properties.scheduling.preemptible = False
    # new_template.properties.scheduling.instance_termination_action = "UNDEFINED_INSTANCE_TERMINATION_ACTION"
    # new_template.properties.scheduling.provisioning_model = 'STANDARD'
    
    # MARK: SPOT 인스턴스 사용하는 경우.                
    new_template.properties.scheduling.preemptible = True
    new_template.properties.scheduling.instance_termination_action = "TERMINATE"
    new_template.properties.scheduling.provisioning_model = 'SPOT'
                                    
    # 새로운 템플릿 생성 요청
    operation = client.insert(
        project=project_id,
        instance_template_resource=new_template
    )
    
    return operation

def wait_for_operation(operation: compute_v1.Operation, project_id: str):
    """작업 완료를 기다립니다."""
    client = compute_v1.GlobalOperationsClient()
    return client.wait(project=project_id, operation=operation.name)

def clone_template_with_new_network(
    project_id,
    source_template, 
    new_region,
    env_vars: dict
    ) -> str:
        
    new_template = f"temp-{new_region}-{source_template}"    
    new_subnet = f"projects/{project_id}/regions/{new_region}/subnetworks/default" # subnet name is default
    
    operation = create_modified_template(
        project_id=PROJECT_ID,
        source_template_name=source_template,
        new_template_name=new_template,
        new_subnet=new_subnet,
        new_region=new_region,
        env_vars=env_vars
    )
    
    # 작업 완료 대기
    wait_for_operation(operation, project_id)
    print(f"Successfully created new template: {new_template}")
    return new_template            
    

def delete_instance_template(project_id: str, template_name: str) -> compute_v1.Operation:
    """인스턴스 템플릿을 삭제합니다."""
    client = compute_v1.InstanceTemplatesClient()    
    return client.delete(project=project_id, instance_template=template_name)

# MARK: 반드시 JOB 완료 이후에 삭제해야 함.
def delete_template(project_id, template_name):
    try:
        operation = delete_instance_template(project_id, template_name)
        wait_for_operation(operation, project_id)
        print(f"Successfully deleted template: {template_name}")
    except Exception as e:
        print(f"Error deleting template: {str(e)}")

def create_gpu_job(project_id, zones:List[str], new_template, env_vars:dict):
    client = batch_v1.BatchServiceClient()        
    region = "-".join(zones[0].split("-")[:2])

    print("env_vars:", env_vars.items())
      
    images_uri = f'asia-northeast3-docker.pkg.dev/{project_id}/{REPOSITORY}/{IMAGE_NAME}:{TAG}'    

    task_group = batch_v1.TaskGroup()
    task_spec = batch_v1.TaskSpec()
    
    # spec for task. Do not over InstanceTemplate
    compute_resource = batch_v1.ComputeResource()
    compute_resource.cpu_milli = 2000
    compute_resource.memory_mib = 7500
    
    runnables = batch_v1.Runnable()
    runnables.environment.variables = env_vars
    runnables.container = batch_v1.Runnable.Container()
    runnables.container.image_uri = images_uri
    task_spec.runnables = [runnables]
    
    allocation_policy = batch_v1.AllocationPolicy()    
    instances = batch_v1.AllocationPolicy.InstancePolicyOrTemplate()    
    if new_template:
        instances.instance_template = new_template
    
    # MARK: InstanceTemplate 미사용으로 주석 처리    
    # policy = batch_v1.AllocationPolicy.InstancePolicy()
    # policy.machine_type = 'n1-standard-4'
    # policy.boot_disk.type_ = 'pd-ssd'
    # policy.boot_disk.size_gb = 50
    # policy.provisioning_model = 'SPOT'    
    
    # accelerators = batch_v1.AllocationPolicy.Accelerator()
    # accelerators.type_ = 'nvidia-tesla-t4'
    # accelerators.count = 1
    # policy.accelerators = [accelerators]    
    
    location = batch_v1.AllocationPolicy.LocationPolicy()    
    location.allowed_locations = [f"zones/{zone}" for zone in zones]
    
    allocation_policy.instances = [instances]
    allocation_policy.location = location
    
    logs_policy = batch_v1.LogsPolicy()
    logs_policy.destination = 'CLOUD_LOGGING'
    
    network_policy = batch_v1.AllocationPolicy.NetworkPolicy()
    
    network_interface = batch_v1.AllocationPolicy.NetworkInterface()    
    network_interface.network = f'projects/{project_id}/global/networks/default'    
    network_interface.subnetwork = f'projects/{project_id}/regions/{region}/subnetworks/default'
        
    network_policy.network_interfaces = [network_interface]
    
    allocation_policy.network = network_policy
    
    # 기존: OS 차이로 인한 이슈 발생
    # job = {
    #     "task_groups":[
    #         {
    #             "task_spec":{
    #                 "runnables": [{                        
    #                     # cloud-init을 대신 주입함
    #                     # "environment": {
    #                     #         "variables": env_vars
    #                     #     },
    #                     "container": {
    #                         "image_uri": images_uri,                                                                                                                                         
    #                     }
    #                 }],                   
    #                 # Should be compatible with instance_template             
    #                 "compute_resource": { 
    #                     "cpu_milli": 2000,
    #                     "memory_mib": 7500,
    #                 },
    #             },
    #             "task_count": 1,
    #             "parallelism": 1            
    #         },            
    #     ],
    #     "allocation_policy": {
    #         "instances": [                
    #             { 
    #                 "instance_template": new_template,                    
    #             }
    #         ],
    #         "location": {
    #             "allowed_locations": [f"zones/{zone}" for zone in zones] # multi-zone
    #                 # [f"zones/{zone}"]                    
    #         },
    #         "network": {
    #             "network_interfaces": [
    #                 {
    #                     "network": f'projects/{project_id}/global/networks/{VPC_NAME}',
    #                     "subnetwork": f'projects/{project_id}/regions/{region}/subnetworks/default'
    #                 }
    #             ]
    #         },
    #     },
    #     "logs_policy": {
    #         "destination": "CLOUD_LOGGING",
    #     }
    # }           
    
    # NEW: cloud-init 미주입
    nvidia_gpu_options = "--volume /var/lib/nvidia/lib64:/usr/local/nvidia/lib64 --volume /var/lib/nvidia/bin:/usr/local/nvidia/bin --device /dev/nvidia0:/dev/nvidia0 --device /dev/nvidia-uvm:/dev/nvidia-uvm --device /dev/nvidiactl:/dev/nvidiactl -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=all --env LD_LIBRARY_PATH=/usr/local/nvidia/lib64"
    transformers_module_options = "-e TRANSFORMERS_CACHE=/app"
    custom_options = " ".join([f"-e {k}={v}" for k, v in env_vars.items()])
    options = f"{nvidia_gpu_options} {transformers_module_options} {custom_options}"
    job = {
        "task_groups":[
            {
                "task_spec":{
                    "runnables": [{                        
                        # cloud-init을 대신 주입함. X
                        # "environment": {
                        #         "variables": env_vars
                        #     },s
                        
                        # 그냥 아래처럼 넣어서 하면 됨. env_vars를 같이 넣어서 사용하자.
                        "container": {
                            "image_uri": images_uri,                                                                                     
                            "entrypoint": "",
                            "volumes": [],
                            "options": options
                            }
                    }],                   
                    # Should be compatible with instance_template
                    "compute_resource": { 
                        "cpu_milli": 2000,
                        "memory_mib": 7500,
                    },
                },
                "task_count": 1,
                "parallelism": 1            
            },            
        ],
        "allocation_policy": {
            "instances": [
            {
                "install_gpu_drivers": True,
                "policy": {
                    # "provisioning_model": "SPOT",
                    "machine_type": "n1-standard-2",
                    "accelerators": [
                        {
                            "type_": "nvidia-tesla-t4",
                            "count": "1"
                        }
                    ],
                    "boot_disk": {
                        "size_gb": "50"
                    }
                }
            }
        ],
            "location": {
                "allowed_locations": [f"zones/{zone}" for zone in zones] # multi-zone
                    # [f"zones/{zone}"]                    
            },
            "network": {
                "network_interfaces": [
                    {
                        "network": f'projects/{project_id}/global/networks/{VPC_NAME}',
                        "subnetwork": f'projects/{project_id}/regions/{region}/subnetworks/default'
                    }
                ]
            },
        },
        "logs_policy": {
            "destination": "CLOUD_LOGGING",
        }
    }            
    
    # job = batch_v1.Job()
    # job.task_groups = [task_group]
    # job.allocation_policy = allocation_policy
    # job.logs_policy = logs_policy
    
    # create_request = batch_v1.CreateJobRequest()
    # create_request.parent = f'projects/{project_id}/locations/{zone}'
    # create_request.job = job            
    
    
    # 여기서 metadata 등록 가능...
    # response = client.create_job(request=create_request, metadata=metadata)    
    parent = f'projects/{project_id}/locations/{region}'
    
    response = client.create_job(
        job=job, 
        parent=parent,
        retry=no_retry,    
        timeout=timeout    
        )
    print(f"Created job: {response.name}")
    return response

def check_resource_errors(status_events):
    error_keywords = [
        "CODE_GCE_ZONE_RESOURCE_POOL_EXHAUSTED",
        "does not have enough resources available",
        "inadequate quotas",
    ]
    
    for event in status_events:
        print(f"Event: {event.description}")
        for keyword in error_keywords:
            if keyword in event.description:
                return True, event.description
    return False, None

def wait_until_job(job_name, new_template, max_wait_seconds=600):
    client = batch_v1.BatchServiceClient()        
    enum_dict = {v: k for k, v in batch_v1.JobStatus.State.__dict__.items() if not k.startswith('_')}
    
    start_time = time.time()
    try:
        while time.time() - start_time < max_wait_seconds:
            response = client.get_job(name=job_name, retry=no_retry, timeout=timeout)            
            state = response.status.state
            
             # 리소스 에러 체크
            has_error, error_msg = check_resource_errors(response.status.status_events)
            if has_error:
                print(f"Resource error detected: {error_msg}")
                print("Terminating job...")
                client.delete_job(name=job_name)
                return False            
            
            if state == batch_v1.JobStatus.State.FAILED:
                return False
            elif state == batch_v1.JobStatus.State.DELETION_IN_PROGRESS:
                return False
            elif state == batch_v1.JobStatus.State.RUNNING:                
                return True
            else:                                
                print(f"Job status: {enum_dict[state]}. Waiting...")
                time.sleep(10)
        
        print("Job did not complete within the time limit.")
        # client.delete_job(name=job_name) # Debug 시에는 주석 처리
        return False
            
    except Exception as e:
        print(f"Error getting job status: {str(e)}")
        return False
    # finally:
    #     delete_template(PROJECT_ID, new_template)

def deploy_review_jobs():
    region_to_zones = {}
    env_vars = {
        "MODEL_PATH": os.getenv("MODEL_PATH", "answerdotai/ModernBERT-base"),
        "BATCH_SIZE": os.getenv("BATCH_SIZE", 8)
    }    
    for zone in ZONES.split(","):
        region = "-".join(zone.split("-")[:2])
        if region not in region_to_zones:
            region_to_zones[region] = []
        region_to_zones[region].append(zone)
    
    for region, zones in region_to_zones.items():
        print(f"Deploying to region: {region}")
        new_template = clone_template_with_new_network(PROJECT_ID, "batch-kluebert-ocr-template", region, env_vars)
        new_template = None
        try:
            job = create_gpu_job(PROJECT_ID, zones, new_template, env_vars)
            if wait_until_job(job.name, new_template):
                print(f"Job {job.name} is successfully RUNNNING: {region}")
                break
            else:
                print(f"Job failed. Move to the next region from {region}.")        
        except Exception as e:
            print(f"Error deploying to region {region}: {str(e)}")
            # delete_template(PROJECT_ID, new_template)
            continue
        # finally:
        #     # clean up
        #     delete_template(PROJECT_ID, new_template)
            
    

if __name__ == "__main__":
    deploy_review_jobs()