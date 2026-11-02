from abc import ABC, abstractmethod
import cv2


class ImageFilter(ABC):
    @abstractmethod
    def apply(self, image):
        pass

class MedianFilter(ImageFilter):
    # 方案 A：中值濾波器 (Median Filter) —— 對去除「椒鹽噪點(突發性雜訊)」效果極佳，且非常能保留邊緣，很適合 Aruco 定位
    # 參數 5 代表 5x5 的矩陣視窗，必須是奇數
    def __init__(self, k_size=5):
        self.k_size = k_size

    def apply(self, image):
        return cv2.medianBlur(image, self.k_size)


class BilateralFilter(ImageFilter):
    # 方案 B：雙邊濾波器 (Bilateral Filter) —— 類似高功率降噪 (Power Noise Filter)，能在強效降噪的同時，極致地保留 Aruco 的銳利邊緣
    # 參數說明：9(鄰域直徑), 75(顏色空間標準差), 75(坐標空間標準差)

    def __init__(self, d=9, sigmaColor=75, sigmaSpace=75):
        self.d = d
        self.sigmaColor = sigmaColor
        self.sigmaSpace = sigmaSpace

    def apply(self, image):
        return cv2.bilateralFilter(image, self.d, self.sigmaColor, self.sigmaSpace)

class NlmFilter(ImageFilter):
    # OpenCV 的非局部均值去噪 (NLM) 參數說明：
    # src: 輸入的 BGR 影像
    # h: 決定亮度通道的濾鏡強度 (數值越大去噪越強，但容易抹掉細節，通常設 3 ~ 10)
    # hForColorComponents: 色彩通道的強度 (通常設與 h 相同)
    # templateWindowSize: 尋找相似區塊的模板大小 (建議設奇數，如 7)
    # searchWindowSize: 搜尋區域的大小 (建議設奇數，如 21)
    def __init__(self, h=10, templateWindowSize=7, searchWindowSize=21):
        self.h = h
        self.templateWindowSize = templateWindowSize
        self.searchWindowSize = searchWindowSize

    def apply(self, image):
        return cv2.fastNlMeansDenoisingColored(src = image,
                                               dst=None,
                                               h=self.h,
                                               templateWindowSize=self.templateWindowSize,
                                               searchWindowSize=self.searchWindowSize)


def ResizeByTotalPixelsFilter(image, pixel_limit):
        h, w = image.shape[:2]
        ratio = (h*w) / pixel_limit
        divider = ratio ** 0.5
        #print(f'scaling ratio = {ratio} W = {w//divider}, H = {h//divider}')
        interpolation_algorithm = cv2.INTER_AREA if ratio > 1.0 else cv2.INTER_CUBIC

        resized_image = cv2.resize(image, (int(w // divider), int(h // divider)), interpolation=interpolation_algorithm)

        return resized_image