import json

def get_all_data():
    """
    Returns all the data for the feature tracer.
    In a real application, this would fetch data from a database.
    """
    return {
        "summary": {
            "total_features": 3000,
            "completed_features": 1950,
            "in_progress_features": 750,
            "not_started_features": 300,
            "last_updated": "2025年7月18日 14:30"
        },
        "domains": [
            {
                "name": "内存管理",
                "total_features": 420,
                "completed": 328,
                "in_progress": 65,
                "not_started": 27,
                "icon": "fa-microchip",
                "features": [
                    {"name": "虚拟内存管理", "description": "支持分页和分段", "status": "已完成"},
                    {"name": "内存分配算法", "description": "Buddy和Slab分配器", "status": "已完成"},
                    {"name": "内存保护机制", "description": "实现内存访问控制", "status": "进行中"},
                    {"name": "内存压缩", "description": "提高内存利用率", "status": "进行中"},
                    {"name": "内存热插拔支持", "description": "动态添加/移除内存", "status": "未开始"}
                ]
            },
            {
                "name": "文件系统",
                "total_features": 380,
                "completed": 247,
                "in_progress": 85,
                "not_started": 48,
                "icon": "fa-folder-open"
            },
            {
                "name": "进程调度",
                "total_features": 290,
                "completed": 238,
                "in_progress": 42,
                "not_started": 10,
                "icon": "fa-tasks"
            },
            {
                "name": "网络协议",
                "total_features": 450,
                "completed": 248,
                "in_progress": 125,
                "not_started": 77,
                "icon": "fa-wifi"
            },
            {
                "name": "设备驱动",
                "total_features": 520,
                "completed": 234,
                "in_progress": 182,
                "not_started": 104,
                "icon": "fa-plug"
            },
            {
                "name": "安全机制",
                "total_features": 440,
                "completed": 317,
                "in_progress": 83,
                "not_started": 40,
                "icon": "fa-lock"
            }
        ]
    }
