from abc import ABC, abstractmethod
import argparse
import logging
import sys, os
import configparser

class MainProgramFacilities(ABC):
    """
    1. option argument
    2. system logger
    3. configuration
    """
    def __init__(self, description: str = "應用程式命令列介面"):
        self.parser = argparse.ArgumentParser(description=description)
        # 內建廠務：直接提供預設的全域 Options
        self.parser.add_argument("-v", "--verbose", action="store_true", help="啟用詳細 Log 輸出")

        # 讓子類別有機會宣告自己專屬的 options
        self.setup_options()


    @abstractmethod
    def setup_options(self):
        """子類別可以覆寫此方法，明確寫出自己需要的 Options。
            self.add_option("-p", "--port", type=int, default=8080, help="服務連接埠")
            if no further options, use pass
        """
        pass

    @abstractmethod
    def _init_configure(self, config_filepath):
        pass
    def add_option(self, short: str, long: str, **kwargs):
        """提供給子類別的標準工具，用來註冊參數。"""
        self.parser.add_argument(short, long, **kwargs)

    def _init_logger(self, verbose: bool):
        """完全隱藏的 Logger 廠務設定"""
        self.logger = logging.getLogger()
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # 🎯 2. 【動態插拔輸出端 A】：設定螢幕輸出 (Console)
        console_handler = logging.StreamHandler()
        # 螢幕上講話要精簡、漂亮 [▶️ INFO | 訊息]
        console_formatter = logging.Formatter(f"[%(funcName)s]▶️ %(levelname)-8s | %(message)s")
        console_handler.setFormatter(console_formatter)

        # ✨ 【關鍵修正】：必須同時調低 Logger 本身的層級關卡
        if verbose:
            self.logger.setLevel(logging.DEBUG)  # 讓 Logger 本身願意接收 DEBUG 訊息
            console_handler.setLevel(logging.DEBUG)

        else:
            self.logger.setLevel(logging.INFO)
            console_handler.setLevel(logging.INFO)

        # 🛡️ 螢幕防禦：不論全域開多大，螢幕上「永遠只印 INFO 以上」的日常報告，拒絕 DEBUG 碎碎念刷屏！
        self.logger.addHandler(console_handler)

    @abstractmethod
    def main(self, args: argparse.Namespace):
        """強迫子類別必須實作的核心業務。
        直接把解析好的 args 丟進來，子類別要什麼自己拿，極度直覺！
        """
        pass

    def run(self):
        """程式開工總指揮"""
        parsed_args = self.parser.parse_args()

        # 初始化廠務 Logger
        self._init_logger(parsed_args.verbose)

        try:
            self._init_configure(parsed_args.config)
            # 呼叫業務生產線
            self.main(parsed_args)
        except Exception as e:
            self.logger.error(f"執行時發生錯誤: {e}")
            sys.exit(1)


