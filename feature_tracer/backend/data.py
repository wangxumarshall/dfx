
import json

data = {
    "summary": {
        "total_features": 3000,
        "completed_features": 1950,
        "in_progress_features": 750,
        "not_started_features": 300,
        "last_updated": "2025年7月18日 14:30"
    },
    "domains": [
        {
            "id": "memory-management",
            "name": "内存管理",
            "total_features": 420,
            "completed": 328,
            "in_progress": 65,
            "not_started": 27,
            "icon": "fa-microchip",
            "features": [
                {"id": "virtual-memory", "name": "虚拟内存管理", "description": "支持分页和分段", "status": "已完成"},
                {"id": "memory-allocation", "name": "内存分配算法", "description": "Buddy和Slab分配器", "status": "已完成"},
                {"id": "memory-protection", "name": "内存保护机制", "description": "实现内存访问控制", "status": "进行中"},
                {"id": "memory-compression", "name": "内存压缩", "description": "提高内存利用率", "status": "进行中"},
                {"id": "memory-hotplug", "name": "内存热插拔支持", "description": "动态添加/移除内存", "status": "未开始"}
            ]
        },
        {
            "id": "file-system",
            "name": "文件系统",
            "total_features": 380,
            "completed": 247,
            "in_progress": 85,
            "not_started": 48,
            "icon": "fa-folder-open"
        },
        {
            "id": "process-scheduling",
            "name": "进程调度",
            "total_features": 290,
            "completed": 238,
            "in_progress": 42,
            "not_started": 10,
            "icon": "fa-tasks"
        },
        {
            "id": "network-protocol",
            "name": "网络协议",
            "total_features": 450,
            "completed": 248,
            "in_progress": 125,
            "not_started": 77,
            "icon": "fa-wifi"
        },
        {
            "id": "device-driver",
            "name": "设备驱动",
            "total_features": 520,
            "completed": 234,
            "in_progress": 182,
            "not_started": 104,
            "icon": "fa-plug"
        },
        {
            "id": "security-mechanism",
            "name": "安全机制",
            "total_features": 440,
            "completed": 317,
            "in_progress": 83,
            "not_started": 40,
            "icon": "fa-lock"
        }
    ]
}

def get_all_data():
    """
    Returns all the data for the feature tracer.
    """
    return data

def get_domain_by_id(domain_id):
    """
    Returns a single domain by its ID.
    """
    for domain in data['domains']:
        if domain['id'] == domain_id:
            return domain
    return None

def update_feature_status(domain_id, feature_id, new_status):
    """
    Updates the status of a feature.
    """
    domain = get_domain_by_id(domain_id)
    if domain and 'features' in domain:
        for feature in domain['features']:
            if feature['id'] == feature_id:
                feature['status'] = new_status
                return True
    return False

