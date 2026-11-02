import rawpy
import numpy as np
from PIL import Image
import cv2          # pip install openCV-python
import logging
from imageProcessig.imageEnhancer import MedianFilter, BilateralFilter, NlmFilter, ResizeByTotalPixelsFilter
from pathlib import Path

from utils.errorStatusReport import Result


class RawImagePipeline:
    GAMMA={'bt709':(2.2, 4.5), 'sRGB':(2.4, 12.92), 'Linear': (1,1)}
    def __init__(self):
        self.logger = logging.getLogger("Job.RawImagePipeline")
        self.img_buffer = None

    def _init_isp_param(self, gamma=GAMMA['bt709'], no_auto_bright=False):
        ''' Init an Image pipeline of configurations '''
        fbdd_NR = rawpy.FBDDNoiseReductionMode.Full    # Default Off Full, Light
        cfa = rawpy.DemosaicAlgorithm.DHT              # Default AHD, AAHD, DHT ...
        median_filter_passes = 1                       # Default 0

        color_space = rawpy.ColorSpace.Adobe           # Default sRGB, Adobe
        wavelet_noise_threshold= None                  # Default None 100 - 1000 BUG to enabe (BUG)

        user_black  = None                              # Default None (float)
        user_sat    = None                                # Default None (float) custom white level
        #no_auto_scale = False                          # Deafult False, means will auto scale
        adjust_maximum_thr = 0.75                   # Default 0.75, auto adjust max value based on real channel data.
                                                    # if set to greater than 0.99999, default value used
                                                    # if less than 0.0001 no maximum adjust will be performed

        #bright = (1/(1-(512/4096)))**2                               # Default 1.0, brightness scaling
        bright = 1.0                              # Default 1.0, brightness scaling
        auto_bright_thr= None                       # ratio of clipped pixels when automatic brightness increase is used ?
        highlight_mode = rawpy.HighlightMode.Clip   # Default Clip, Blend, Ignore

        #exp_shift = None                            # Deafult None exposure shiift in linear scale, from 0.25 (2-stop darker) - 8.0 (3-stop  lighter)
        exp_shift = None                            # Deafult None exposure shiift in linear scale, from 0.25 (2-stop darker) - 8.0 (3-stop  lighter)
        exp_preserve_highlights = 0.0               # Default 0.0 preserve highlights when lightening the image with exp_shift, from 0.0 to 1.0 (Full preseving)

        params = rawpy.Params( use_camera_wb        = True,
                               no_auto_bright       = no_auto_bright,
                               gamma                = gamma,
                               user_black           = user_black,
                               user_sat             = user_sat,
                               fbdd_noise_reduction = fbdd_NR,                  # Fake Before Demosaicing Denoising
                               median_filter_passes = median_filter_passes,
                               noise_thr            = wavelet_noise_threshold,  #
                               demosaic_algorithm   = cfa,
                               output_color         = color_space,
                               bright               = bright,
                               exp_shift            = exp_shift,
                               exp_preserve_highlights = exp_preserve_highlights,
                               half_size=False
                            )
        return params


    def load_image(self, image_filepath)->Result[bytes]:
        ''' load either standard format image or RAW data image '''
        self.img_buffer = None
        # ======= 1. 格式調和層：不管是哪種檔案，出來一律是相同的 BGR Buffer =======
        filename = Path(image_filepath).name
        try:
            with rawpy.imread(image_filepath) as raw:
                rgb_arr = self.raw2image_convert(raw)
                self.img_buffer = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
                self.logger.info(f"{filename} is decoded  as RAW format")
        except Exception as e:
            self.logger.warning(f"load_image: rawpy.imread NOT Supported with Exception {e}")

        # Fallback: 如果 Pillow 失敗，嘗試用 rawpy 讀取 RAW 檔
        if self.img_buffer is None:
            try:
                with Image.open(image_filepath) as img:
                    rgb_arr = np.array(img.convert('RGB'))
                    # cv2.cvtColor 會複製記憶體，自動將 Pillow 的唯讀/非連續特性，轉為標準可寫入、連續的 BGR Buffer
                    self.img_buffer = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
                    self.logger.info(f"{filename} is STANDARD image format")
            except Exception as e:
                self.logger.error(f"load_image: Image.open failed with Exception {e}")
                #raise ValueError(f"無法讀取影像檔案，不屬於支援的一般影像或 RAW 格式。錯誤: {e}")
                return Result.fail(
                    error_code="UNSUPPORTED_FORMAT",
                    error_message=f"不支援的格式：{Path(image_filepath).name}"
                )
        self.logger.debug(f"成功讀取 image buffer")
        return Result.success(self.img_buffer)


    def raw2image_convert(self, raw, auto=True):
        params = self._init_isp_param(no_auto_bright=not auto)
        rgb_arr = raw.postprocess(params)
        return rgb_arr

    def save(self, filepath:str):
        if self.img_buffer is not None:
            if Path(filepath).suffix.lower() in  [".jpg", "jpeg"]:
                cv2.imwrite(filepath, self.img_buffer, [cv2.IMWRITE_JPEG_QUALITY, 100])
            else:
                cv2.imwrite(filepath, self.img_buffer)


#-------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from pathlib import Path

    isp = RawImagePipeline()
    #file_path = 'IMG_8690.DNG'
    file_path = "/imageProcessig/image/arucoFailed1.nef"
    #file_path = "/Users/norman/PycharmProjects/eShade2ndGen/src/exeImagePreProc/image/unresolved.dng"
    #file_path = "/Users/norman/PycharmProjects/eShade2ndGen/src/exeImagePreProc/image/IMG_8847.jpg"
    #file_path = "/Users/norman/PycharmProjects/eShade2ndGen/src/exeImagePreProc/raw_isp.py"

    try:
        img_buffer = isp.load_image(file_path)

        h, w = img_buffer.shape[:2]
        print(f'{Path(file_path).name} in type({type(img_buffer)}) : HxW = {h}x{w}')

        isp.save("image/aaa.tif")
        #medianFilter = MedianFilter()
        #img_buffer = medianFilter.apply(img_buffer)

        #resizer = ResizeByTotalPixelsFilter(2000*1500)
        #img_buffer = resizer.apply(img_buffer)

        #img_buffer = isp.nlm_denoise(img_buffer)

        cv2.imshow("", img_buffer)

        print("視窗已彈出，請在視窗畫面上按下『任意鍵』來關閉視窗並繼續執行程式...")

        # 4. 關鍵步驟：等待使用者按下鍵盤任意鍵（參數 0 代表無限期等待）
        # 如果沒加這一行，視窗會一閃而過甚至直接當掉
        cv2.waitKey(0)

        # 5. 關閉所有彈出的 OpenCV 視窗，釋放系統資源
        cv2.destroyAllWindows()
    except Exception as e:
        print(f'Exception {e}')

    print(f'Enf of Program')
