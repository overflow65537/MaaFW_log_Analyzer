import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import re

class LogAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MAA 日志分析工具")
        
        # 创建界面组件
        self.create_widgets()
        
    def create_widgets(self):
        # 文件选择区域
        file_frame = ttk.Frame(self.root)
        file_frame.pack(pady=10, fill=tk.X)
        
        ttk.Button(file_frame, text="选择日志文件", command=self.load_file).pack(side=tk.LEFT)
        self.file_label = ttk.Label(file_frame, text="未选择文件")
        self.file_label.pack(side=tk.LEFT, padx=10)
        
        # 搜索条件区域
        search_frame = ttk.Frame(self.root)
        search_frame.pack(pady=10, fill=tk.X)
        
        ttk.Label(search_frame, text="任务名称:").pack(side=tk.LEFT)
        self.task_entry = ttk.Entry(search_frame, width=30)
        self.task_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="开始分析", command=self.analyze_log).pack(side=tk.LEFT)
        
        # 结果显示区域
        result_frame = ttk.Frame(self.root)
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_area = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            width=100,
            height=30,
            font=('Consolas', 9)
        )
        self.result_area.pack(fill=tk.BOTH, expand=True)
        
    def load_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("日志文件", "*.log"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_label.config(text=file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                self.log_data = f.readlines()
                
    def analyze_log(self):
        if not hasattr(self, 'log_data'):
            return
            
        target_task = self.task_entry.get().strip()
        self.result_area.delete(1.0, tk.END)
        
        # 修改正则表达式添加目标任务匹配
        pattern = re.compile(
            r'\[(.*?)\]'  # 时间戳
            r'\[.*?(Px\d+).*?(Tx\d+).*?\]'  # 进程和线程ID
            r'.*?MaaNS::VisionNS::OCRer::analyze\]\s+' + re.escape(target_task) + 
            r'\s+\[uid_=(\d+)\].*?\[all_results_=(\[.*?\])\]\s*'  # 精确匹配all_results的JSON数组
            r'.*?\[param_\.model=([^,\]]*)' 
            r'.*?\[param_\.only_rec=([^,\]]*)' 
            r'.*?\[param_\.expected=\[([^\]]+)'
        )

        for line in self.log_data:
            match = pattern.search(line)
            if match:
                # 修正捕获组顺序
                timestamp, process_id, thread_id, uid, results, \
                model_name, only_rec, expected = match.groups()
                
                # 处理空模型名
                model_display = model_name if model_name.strip() else "默认模型"
                only_rec_display = "仅识别" if only_rec == "true" else "检测+识别"
                
                # 格式化输出新增信息
                self.result_area.insert(tk.END, 
                    f"[{timestamp}] [{process_id}/{thread_id}]\n"
                    f"任务: {target_task} [UID: {uid}]\n"  # 使用输入的target_task
                    f"模型: {model_display} | 模式: {only_rec_display}\n"
                    f"Expected: {expected}\n"
                )
                expected_list = [x.strip('"') for x in expected.split(",")]
                
                # 增强OCR结果的正则匹配
                ocr_pattern = re.compile(r'\{\s*"box":\s*\[(.*?)\]\s*,\s*"score":\s*([\d.]+)\s*,\s*"text":\s*"((?:[^"\\]|\\.)*)"\s*\}')
                
                for result in ocr_pattern.finditer(results):
                    box, score, text = result.groups()
                    
                    clean_text = text.strip()
                    
                    if clean_text in expected_list:
                        self.result_area.insert(tk.END,
                            f"✓ 已命中 | ROI: {box} | 识别文本: {clean_text} | 置信度: {float(score):.4f}\n"
                        )
                    else:
                        self.result_area.insert(tk.END, 
                            f"⚠ 未命中 | ROI: {box} | 识别文本: {clean_text} | 置信度: {float(score):.4f}\n"
                        )
                
                # 仅在完全没有OCR结果时显示提示
                if not ocr_pattern.search(results):
                    self.result_area.insert(tk.END, "⚠ 未命中 - 未找到任何识别结果\n")
                
                self.result_area.insert(tk.END, "-"*100 + "\n\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = LogAnalyzerApp(root)
    root.mainloop()
