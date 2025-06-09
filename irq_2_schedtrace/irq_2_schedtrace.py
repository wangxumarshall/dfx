import re
import sys
import argparse
import logging
from typing import Dict, Optional

def setup_logging():
    """配置日志记录"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def parse_raw_line(line: str) -> Dict[str, str]:
    """解析原始数据行，提取关键信息"""
    patterns = {
        'timestamp': r'\[(\d+\.\d+)\]',
        'cpu': r'\[cpu=(\d+)\]',
        'irqno': r'irqno=(\d+)',
        'thread_name': r'tcb=\'([^\']+)\'',
        'priority': r'prio=(\s*\d+)',
        'actv_name': r'actv=\'([^\']+)\'',
        'idx': r'idx\s*(\d+)'
    }
    
    parsed = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, line)
        if not match:
            raise ValueError(f"无法在该行中找到{field}: {line}")
        parsed[field] = match.group(1).strip()
    
    return parsed

def generate_switch_line(prev_comm: str, prev_pid: str, prev_prio: str, prev_state: str,
                         next_comm: str, next_pid: str, next_prio: str,
                         timestamp: str, cpu: str, idx: str) -> str:
    """生成一行转换后的sched_switch数据"""
    cpu_formatted = f"{int(cpu):03d}"
    
    if prev_comm.startswith('idle/'):
        prefix = f"{prev_comm}-{prev_pid}"
        process_id = "(0)"
    else:
        prefix = f"irqno-{prev_pid}"
        process_id = f"({idx}00)"
    
    return (f"{prefix} {process_id} [{cpu_formatted}] d..2 {timestamp}: "
            f"sched_switch: prev_comm={prev_comm} prev_pid={prev_pid} "
            f"prev_prio={prev_prio} prev_state={prev_state} ==> "
            f"next_comm={next_comm} next_pid={next_pid} next_prio={next_prio}")

def convert_raw_data(input_file: str, output_file: str, max_lines: int = 1728270, 
                     batch_size: int = 10000) -> None:
    """将原始数据文件转换为目标格式并写入输出文件，使用批处理提高效率"""
    logger = setup_logging()
    total_lines = 0
    batch_count = 0
    
    try:
        with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
            batch = []
            for line in f_in:
                if total_lines >= max_lines:
                    logger.info(f"已达到最大处理行数 {max_lines}，停止处理")
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    parsed = parse_raw_line(line)
                except ValueError as e:
                    logger.warning(f"解析错误: {e}")
                    continue
                
                idle_thread = f"idle/{parsed['cpu']}"
                
                # 生成两行转换结果
                line1 = generate_switch_line(
                    prev_comm=idle_thread,
                    prev_pid="0",
                    prev_prio=parsed['priority'],
                    prev_state="R+",
                    next_comm="irqno",
                    next_pid=parsed['irqno'],
                    next_prio=parsed['priority'],
                    timestamp=parsed['timestamp'],
                    cpu=parsed['cpu'],
                    idx=parsed['idx']
                )
                
                timestamp_float = float(parsed['timestamp'])
                new_timestamp = timestamp_float + 0.000001
                line2 = generate_switch_line(
                    prev_comm="irqno",
                    prev_pid=parsed['irqno'],
                    prev_prio=parsed['priority'],
                    prev_state="S",
                    next_comm=idle_thread,
                    next_pid="0",
                    next_prio=parsed['priority'],
                    timestamp=f"{new_timestamp:.6f}",
                    cpu=parsed['cpu'],
                    idx=parsed['idx']
                )
                
                batch.extend([f"{line1}\n", f"{line2}\n"])
                total_lines += 1
                
                # 批处理写入
                if len(batch) >= batch_size:
                    f_out.writelines(batch)
                    batch = []
                    batch_count += 1
                    if batch_count % 10 == 0:
                        logger.info(f"已处理 {total_lines} 行原始数据")
            
            # 写入剩余批次
            if batch:
                f_out.writelines(batch)
        
        logger.info(f"转换完成，共处理 {total_lines} 行原始数据，结果已保存到 {output_file}")
    
    except Exception as e:
        logger.error(f"转换过程中发生错误: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='将IRQ原始数据转换为目标格式')
    parser.add_argument('input_file', help='输入的原始数据文件路径')
    parser.add_argument('output_file', help='输出的转换后数据文件路径')
    parser.add_argument('--max-lines', type=int, default=1728270, 
                        help='最大处理的原始数据行数')
    parser.add_argument('--batch-size', type=int, default=10000, 
                        help='批处理大小，用于提高写入效率')
    
    args = parser.parse_args()
    
    try:
        convert_raw_data(args.input_file, args.output_file, args.max_lines, args.batch_size)
    except Exception as e:
        sys.exit(f"程序运行失败: {str(e)}")    
