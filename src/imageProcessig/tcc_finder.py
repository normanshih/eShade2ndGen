import logging
import cv2
from cv2 import aruco
import numpy as np
import math
from pathlib import Path
from utils.errorStatusReport import Result

# =================================================
class TCC_CARD_FINDER:
    ''' TCC specific process '''
    def __init__(self):
        self.logger = logging.getLogger("Image.TccCardFinder")
        self.code_set = -1

    def run(self, image)->Result[bytes]:
        self.image = image
        ''' -------------- position ------------------------ '''
        #self.tcc_position_decoder = TCC_POSITION_TAG(debug=True)          # Position Code
        self.tcc_position_decoder = TCC_POSITION_ALGORITHM()          # Position Code

        self.roi_image = self.tcc_position_decoder.get_tcc_roi(self.image)
        self.is_position_found = False
        if self.roi_image is not None:
            self.is_position_found = True

        self.pixel_mm = None
        self.unwarp_roi_image = None
        if self.is_position_found:
            self.pixel_mm = self.tcc_position_decoder.get_pixel_per_mm()
            self.unwarp_roi_image = self.tcc_position_decoder.unwarp_roi()
            self.code_set = self.tcc_position_decoder.get_code_set()
            return Result.success(self.roi_image)
        else:
            return Result.fail(
                error_code="TCC is not found",
                error_message=f"沒有找到 TCC 卡"
            )


    def is_found(self):
        '''
        if Positioning tags detection
        :return: boolean: True or False
        '''
        self.logger.debug(f'TCC Positioning marks is found: {self.is_position_found}')
        return self.is_position_found

    def get_positioned_image(self):
        return self.roi_image

    def get_code_set(self):
        return self.code_set

    def get_colorchecker_image(self, targetWidth = 1000):
        height, width = self.unwarp_roi_image.shape[:2]
        ratio = targetWidth / width
        width = int(width * ratio)
        height = int(height * ratio)
        colorchecker_image = cv2.resize(self.unwarp_roi_image, (width, height), interpolation=cv2.INTER_CUBIC)

        return colorchecker_image

    def get_pixels_mm(self):
        return self.pixel_mm

    def save(self, filepath):
        tcc_image = self.get_colorchecker_image()
        if Path(filepath).suffix.lower() in  [".jpg", "jpeg"]:
            cv2.imwrite(filepath, tcc_image, [cv2.IMWRITE_JPEG_QUALITY, 100])
        else:
            cv2.imwrite(filepath, tcc_image)


# =================================================
class TCC_POSITION_ALGORITHM:
    ''' Core algorithm in detectig ArUco marks in image of TCC colorchecker positioning '''
    def __init__(self, dict = aruco.DICT_4X4_50):
        self.logger = logging.getLogger("Image.TccAlgorithm")
        self.__aruco_dict = aruco.getPredefinedDictionary(dict)
        self.corners_of_markers={}      # dictionary: 'id': [[x1,y1],[x2,y2],[x3,y3],[x4,y4
        self.ids = []                   # list of detected marker IDs
        self.roi_centroid_vertexes=None          #
        self.marker_frame_width  = 0    # frame width (pixel) map to frame size(mm) from QR code to get pixel/mm
        self.marker_frame_height = 0
        self.marker_size ={}           # marker size (pixel)

        self.image = None
        self.roi_image = None

        self.code_set_number = -1    # code set is the id number, e.g. SET0: 0,1,2,3, SET1: 4,5,6,7

    def generate_marker(self, marker_id, marker_size=200, marker_border=1 , filename=None):
        ''' ArUco code generator to encode the marker
            output image file to .png file format
         '''
        markerImage = np.zeros([marker_size, marker_size], np.uint8)
        markerImg = aruco.generateImageMarker(self.__aruco_dict, marker_id, marker_size, markerImage, marker_border)
        if filename is None:
            filename = "aruco_" + str(marker_id).zfill(3) + ".png"
        cv2.imwrite(filename, markerImage)

    def get_code_set(self):
        return self.code_set_number

    def get_tcc_roi(self, image, output_file="debug_aruco_markers.png"):
        '''
        detect TCC position ArUco markers to get:
        1. TCC ROI (distortion corrected colorchecker)
        2. TCC marker frame size

        use 2-phase process, in which the
        1st phase check orientation to align orientation
        2nd phase get ROI

        input image must be in cv2 image format
        :return is_detected, self.roi_image
            self.roi_image    : cv2 image

        '''
        self.image = image

        # 0th-phase decode: to check  mirroring
        status = self.__decode(self.image,output_file='1st_decode.tif')
        if not status:
            #self.__check_mirroring()
            self.image = cv2.flip(self.image, 1)


        # 1st-phase decode: to check orientation(rotate and mirroring)
        status = self.__decode(self.image,output_file='1st_decode.tif')

        if status:
            angle = self.__check_orientation()
            #print(f'1st phase: image angle : {angle}')
            rotated_image = self.__image_rotate(self.image, int(angle))
            self.image = rotated_image

            # 2nd-phase decode
            status2 = self.__decode(self.image, output_file='2nd_decode.tif')
            if status2:
                self.roi_image = self.__roi_crop()
            else:
                self.logger.error(f'get_tcc_roi: 2nd decode Failed')
        else:
            self.logger.error(f'get_tcc_roi: 1st decode Failed')

        return self.roi_image

    def __decode(self, image, output_file = 'debug_decoded_image.tif'):
        '''  '''
        self.corners_of_markers={}      # dictionary: 'id': [[x1,y1],[x2,y2],[x3,y3],[x4,y4
        self.ids = []                   # list of detected marker IDs
        self.roi_centroid_vertexes=None          #

        status = False
        parameters = aruco.DetectorParameters()
        # 核心參數調整：
        # 1. 降低最小標籤邊界特徵的像素大小（預設通常較大）
        parameters.minMarkerPerimeterRate = 0.01  # 允許畫面中極小的 Marker 被偵測（佔螢幕周長比例）default 0.03

        # 2. 調整二值化（Threshold）的視窗大小，適應微小方塊
        parameters.adaptiveThreshWinSizeMin = 3
        parameters.adaptiveThreshWinSizeMax = 23
        parameters.adaptiveThreshWinSizeStep = 5        #default 10

        ## check parameters
        detector = aruco.ArucoDetector(self.__aruco_dict, parameters)
        corners, ids, rejectedImgPoints = detector.detectMarkers(image)


        if corners:
            # 20240407: ids maybe [0,1,2,3], or [4,5,6,7], or maybe any sets in the future
            self.logger.debug(f'detected corner ids are: {ids} ')
            min_id = min(ids)
            self.code_set_number = int(min_id //4)
            offset = int(self.code_set_number*4)
            #print(f'_min_id = {min_id} w/ type={type(min_id)},offset = {offset}')
            ids = [x - offset for x in ids]
            self.logger.debug(f'detected corner ids are: {ids} ')

            for id, corner in zip(ids, corners):
                # 20250526 workaround to solve false ID detected
                if id not in [0,1,2,3]:
                    self.logger.error(f'False ID {id[0]} detected and removed')
                    continue

                self.ids.append(id)
                self.corners_of_markers[id] = corner[0]  # dictionary {id:[corner_vertexex(x0,y0),(x1,y1),(x2,y2),(x3,y3)]


            corner_ids = [0, 1, 2, 3]
            if all(element in self.ids for element in corner_ids):
                status = True
            else:
                self.logger.debug(f'__decode: self.ids = {self.ids}')
                status = self.__exterpolate_missed_point()

        return status

    def __exterpolate_missed_point(self):
        status = False
        if len(self.ids) > 1:
            corner_ids = [0, 1, 2, 3]
            missed_points = list(set(corner_ids) - set(self.ids))

            if len(missed_points) == 1:
                status = self.__missed_one(missed_points)
            else: # 2
                status = self.__missed_two(missed_points)

        return status

    def __missed_one(self, missed_points):
        ''' from 3 points to calculate the missed 4th point '''
        missed_point = missed_points[0]
        center = (missed_point+2) % 4
        vectors = []
        diagonal_vector = None
        for point in self.ids:
            if point == missed_point: continue
            vector = self.__calculate_vector(self.corners_of_markers[center], self.corners_of_markers[point])
            vectors.append(vector)
            if diagonal_vector is None:
                diagonal_vector = vector
            else:
                diagonal_vector +=  vector

        exterpolated_point = self.corners_of_markers[center] + diagonal_vector
        #print(f'exterpolated_point: {exterpolated_point}')
        self.ids.append(missed_point)
        self.corners_of_markers[missed_point] = exterpolated_point

        return True

    def __missed_two(self, missed_points):
        ''' from 2 points to calculate the missed 3rd and 4th point '''
        return False

    def __calculate_vector(self, v1, v2):
        vector = v2 - v1
        return vector

    def __check_orientation(self):
        roi_centroid_vertexes = {}
        corner_ids = [0, 1, 2, 3]
        for id in corner_ids:
            corner = self.corners_of_markers[id]
            roi_centroid_point, marker_size = self.__find_centroid_vertex_of_marker_and_size( corner)
            roi_centroid_vertexes[id] = roi_centroid_point

        angle = self.__is_rotated(roi_centroid_vertexes)
        return angle


    def __check_mirroring(self):
        ''' check if the image is mirroring image'''
        roi_centroid_vertexes = {}
        corner_ids = [0, 1, 2, 3]
        for id in corner_ids:
            corner = self.corners_of_markers[id]
            roi_centroid_point, marker_size = self.__find_centroid_vertex_of_marker_and_size( corner)
            roi_centroid_vertexes[id] = roi_centroid_point
        # caculate vector direction, clockwise or counterclockwise
        print(f'__check_mirroring: roi_centroid_vertexes:{roi_centroid_vertexes}')
        vectors=[]
        for id in corner_ids:
            vector = np.array(roi_centroid_vertexes[(id+1)%4]) - np.array(roi_centroid_vertexes[id])
            print(f'vector = {vector}')
            vectors.append(vector)

        cross_product = vectors[0][0] * vectors[1][1] - vectors[0][1]* vectors[1][0]
        print(f'__check_mirroring: cross_product={cross_product}')

    def __debug_show(self, image, corners = None, ids=None, text='DEBUG_SHOW'):
        debug_image = image.copy()
        if corners is not None and ids is not None:
            debug_image = aruco.drawDetectedMarkers(debug_image, corners, ids, borderColor=(0, 0, 255))

        cv2.imshow(text, debug_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def get_pixel_per_mm(self, frame_width_mm=18.8, frame_height_mm=13.6):
        #print(f"get_pixel_per_mm: frame width={frame_width_mm}mm, height={frame_height_mm}mm")
        width_pixel_mm = round(self.marker_frame_width / frame_width_mm,1)
        height_pixel_mm = round(self.marker_frame_height / frame_height_mm,1)

        ''' debug for further thinking '''
        diff = abs(width_pixel_mm-height_pixel_mm)
        diff_percent = round((diff/width_pixel_mm) * 100,2)
        #print(f'width pix/mm = {width_pixel_mm}, height pix/mm = {height_pixel_mm} diff% = {diff_percent}%')

        ''' To return width_pixel_mm '''
        return width_pixel_mm

    def unwarp_roi(self, output_file="unwarped.tif"):
        ''' unwarp ROI '''
        unwarp = UNWARP()
        #unwarped_image = unwarp.unwarp_image(self.image, self.roi_centroid_vertexes)
        #print(f'unwarp_roi: self.roi_centroid_vertexes = {self.roi_centroid_vertexes}')
        #print(f'unwarp_roi: self.roi_corner = {self.roi_corner}')
        unwarped_image = unwarp.unwarp_image(self.image, self.roi_corner_vertexes)


        return unwarped_image

    def __roi_crop(self, corner_ids=[0, 1, 2, 3],):
        ''' roi coordinate
            ID0: Upper-Right, ID1: Lower-Right, ID2: Lower-Left, ID3: Upper-Left
         '''
        roi_centroid_vertexes = {}
        roi_image = None
        # 1. find centroids and sizes of markers
        for id in corner_ids:
            corner = self.corners_of_markers[id]
            roi_centroid_point, marker_size = self.__find_centroid_vertex_of_marker_and_size(corner)
            roi_centroid_vertexes[id] = roi_centroid_point
            self.marker_size[id] = marker_size
            self.roi_centroid_vertexes = roi_centroid_vertexes

        # 2. find center of colorchecker
        centroids_of_markers=[]
        for center in roi_centroid_vertexes.values():
            centroids_of_markers.append(center)
        center_colorchecker = self.__calculate_centroid_of_points(centroids_of_markers)
        #print(f'center of colorchecker={center_colorchecker}')

        # 3. find nearest point of markers to center of colorchecker
        roi_corner_vertexes = self.__find_nearest_points_to_center(self.corners_of_markers, center_colorchecker)
        self.roi_corner_vertexes = roi_corner_vertexes    # the 4 corner vertexes of ROI

        #self.__calculate_frame_marker_distance_pixels(roi_centroid_vertexes)
        self.__calculate_frame_marker_distance_pixels(roi_corner_vertexes)

        #left, top, right, bottom = self.__from_markers_vertex_to_roi_area(roi_centroid_vertexes)
        left, top, right, bottom = self.__from_markers_vertex_to_roi_area(roi_corner_vertexes)
        roi_image = self.image[top:bottom, left:right].copy()

        return roi_image

    def __calculate_frame_marker_distance_pixels(self, roi_vertexes):
        ''' '''
        distances={}
        for id in range(4):
            x0 = roi_vertexes[id][0]
            y0 = roi_vertexes[id][1]
            id2 = (id+1)%4
            x1 = roi_vertexes[id2][0]
            y1 = roi_vertexes[id2][1]
            a = abs(x0-x1)
            b = abs(y0-y1)
            c = self.__calculate_Pythagorean(a,b)
            #print(f'{id}-{id2} distance: SQRT({a}^2 + {b}^2) =  {c}')
            distances[id]=c

        self.marker_frame_width = int(max(distances[1], distances[3]))
        self.marker_frame_height = int(max(distances[0], distances[2]))
        #print(f'frame_width = {self.marker_frame_width} pixels')
        #print(f'frame_height = {self.marker_frame_height} pixels')

    def __from_markers_vertex_to_roi_area(self, roi_points):
        ''' centroids: dictionary in which includes points [x,y] '''
        #print(f'__from_markers_vertex_to_roi_area: roi_points={roi_points}')
        x = []
        y = []
        for key, centroid in roi_points.items():
            x.append(centroid[0])
            y.append(centroid[1])
        left = int(min(x))
        top = int(min(y))
        right = int(max(x))
        bottom = int(max(y))

        return left, top, right, bottom

    def __image_rotate(self, image, angle):
        ''' coarse angle rotation (no unwarp) to align the ID coordination '''
        height, width = image.shape[:2]
        rotation_matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)

        # Calculate the bounding box of the rotated image
        cosine = np.abs(rotation_matrix[0, 0])
        sine = np.abs(rotation_matrix[0, 1])
        new_width = int(height * sine + width * cosine)
        new_height = int(height * cosine + width * sine)

        # Adjust the rotation matrix to center the rotated image
        rotation_matrix[0, 2] += (new_width - width) / 2
        rotation_matrix[1, 2] += (new_height - height) / 2

        # Apply the rotation using warpAffine
        rotated_image = cv2.warpAffine(image, rotation_matrix, (new_width, new_height))
        return rotated_image

    def __is_rotated(self, centroids):
        ''' to check the orientation (according to marker ID) of markers
            return rotation angle in 90 deg units
        '''
        xs = 0
        ys = 0
        for id in range(0,4):
            xs += centroids[id][0]
            ys += centroids[id][1]
        xs /= 4
        ys /= 4

        angle = 0
        if centroids[0][0] > xs:
            angle += 180
            if centroids[0][1] > ys:
                angle += 90
        else:
            if centroids[0][1] < ys:
                angle += 90
        #print(f'rotated anghle = {angle}')
        return angle

    def __find_centroid_vertex_of_marker_and_size(self,corner):
        ''' find points (e.g. centriod) for corner of ROI'''
        #print(f'__centroid: corner = {corner}')
        ''' simple version: use centroid of corners'''
        centroid = self.__calculate_centroid_of_points(corner)
        marker_size = self.__find_size_of_marker(corner)

        return centroid, marker_size

    def __find_nearest_points_to_center(self,corners, center_colorchecker):
        nearest_vertexes={}
        #print(f'__find_nearest_points_to_center: corners={corners}')
        corner_ids = [0,1,2,3]
        for id in corner_ids:
            corner = corners[id]
            #print(f'id={id}, corner={corner}')
            nearest = self.__find_nearest_point(corner, center_colorchecker)
            nearest_vertexes[id]= nearest
        #print(f'__find_nearest_points_to_center: nearest_vertexes={nearest_vertexes}')
        return nearest_vertexes

    def __find_nearest_point(self, corner, reference_point):
        min_distance=99999999999
        nearest = None
        for point in corner:
            a = abs(point[0]-reference_point[0])
            b = abs(point[1]-reference_point[1])
            distance = self.__calculate_Pythagorean(a,b)
            if distance < min_distance:
                min_distance = distance
                nearest = [int(point[0]), int(point[1])]
        return nearest


    def __get_roi_vertex_of_marker(self, id, corner):
        ''' according to the marker ID to find the roi vertexes'''
        centroid = self.__calculate_centroid_of_points(corner)
        #print(f'__get_roi_vertex_of_marker: id({id}')
        points = self.__define_point(centroid, corner)

        if id == 0:
            point = points[2]
        elif id == 1:
            point = points[3]
        elif id == 2:
            point = points[0]
        else:
            point = points[1]

        return point

    def __define_point(self, centroid, corner):
        points={}
        #print(f'__define_point: corner={corner}')
        for point in corner:
            if point[0] < centroid[0]:
                if point[1] > centroid[1]:
                    #print(f'Lower-Left: {point}')
                    points[0]=point
                else:
                    #print(f'Upper-Left: {point}')
                    points[1]=point
            else:
                if point[1] > centroid[1]:
                    #print(f'Lower-Right: {point}')
                    points[3]=point
                else:
                    #print(f'Upper-Right: {point}')
                    points[2]=point
        return points


    def __calculate_centroid_of_points(self, points):
        ''' calculate centroid of (4) points: list in which is [x,y] '''
        #print(f'__calculate_centroid_of_points: points={points}')
        x = 0
        y = 0
        i = 0
        for point in points:
            #print(f'point={point}')
            x += point[0]
            y += point[1]
            i+=1
        x /= i
        y /= i
        centroid = [int(x),int(y)]
        #print(f'__centroid: sentroid = [{x},{y}]')
        return centroid

    def __find_size_of_marker(self, points):
        ''' find (calculate) size (pixels) of marker edge (no distortion considered) '''
        xs=[]
        ys=[]
        for point in points:
            xs.append(point[0])
            ys.append(point[1])
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        #print(f'__find_width_of_marker: Rectangle min_x:{min_x}, min_y:{min_y}, max_x:{max_x}, max_y:{max_y}')

        width=[]
        height=[]
        for point in points:
            if min_x in point:
                h = point[1]-min_y
                #print(f'__find_width_of_marker: min_x search, point={point}, h={h}')
                height.append(h)
            if max_y in point:
                w =  max_x - point[0]
                #print(f'__find_width_of_marker: min_y search, point={point}, w={w}')
                width.append(w)
        a = min(height)
        b = min(width)
        length = self.__calculate_Pythagorean(a,b)
        #print(f'__find_width_of_marker: w={width}, h={height},a={a}, b={b} length={length}')

        return length

    def __calculate_Pythagorean(self, a, b):
        c = math.sqrt(a**2 + b**2)
        return c


    def __corner_finder(self, vertex):
        corners={}
        centroid = self.__calculate_centroid_of_points(vertex)
        for point in vertex.values():
            if point[0] < centroid[0]:
                if point[1] > centroid[1]:
                    corners['lower-left']=point
                else:
                    corners['upper-left']=point
            else:
                if point[1] > centroid[1]:
                    corners['lower-right']=point
                else:
                    corners['upper-right']=point
        return corners

# =================================================
class UNWARP:
    '''
    UNWARP class define an unwarp engine by which
    unwarp an input distored image to target rectangular image
    '''
    LL = 0;
    UL = 1;
    UR = 2;
    LR = 3
    coordinate_name = {LL: "Lower Left",
                       UL: "Upper Left",
                       UR: "Upper Right",
                       LR: "Lower Right"}

    def unwarp_image(self, image, vertex, aspect_ratio=(18.8/13.6)):
        #print(f'unwarp_image: vertex = {vertex}')
        source_pts = np.float32([[p for p in vertex.values()]])
        #print(f'unwarp_image: source_pts: {source_pts}')
        #print(f'unwarp_image: source_pts = {source_pts}')
        # 計算目標矩形的目標邊長和目標角度（水平角度）
        dX = source_pts[0][UNWARP.LL][0]-source_pts[0][UNWARP.UL][0]
        dY = source_pts[0][UNWARP.LL][1]-source_pts[0][UNWARP.UL][1]
        target_height = math.sqrt(pow(dX,2)+pow(dY,2))
        dX = source_pts[0][UNWARP.LR][0]-source_pts[0][UNWARP.LL][0]
        dY = source_pts[0][UNWARP.LL][1]-source_pts[0][UNWARP.LR][1]
        target_width = math.sqrt(pow(dX,2)+pow(dY,2))

        #print(f'target_height={target_height}, target_width={target_width}')

        # 2023/11/24
        if target_width >= target_height:
            target_height = target_width/aspect_ratio
        else:
            target_width = target_height * aspect_ratio

        #target_height, target_width, _ = image.shape
        target_angle = 0.0
        # 定義源點和目標點
        target_pts = np.float32([[0, target_height - 1],
                                 [0, 0],
                                 [target_width - 1, 0],
                                 [target_width - 1, target_height - 1]])

        # 進行透視變換
        matrix = cv2.getPerspectiveTransform(source_pts, target_pts)
        result_image = cv2.warpPerspective(image, matrix, (int(target_width), int(target_height)))

        return result_image


if __name__ == "__main__":
    from raw_isp import RawImagePipeline


    """完全隱藏的 Logger 廠務設定"""
    logger = logging.getLogger()

    # 🎯 2. 【動態插拔輸出端 A】：設定螢幕輸出 (Console)
    console_handler = logging.StreamHandler()
    # 螢幕上講話要精簡、漂亮 [▶️ INFO | 訊息]
    console_formatter = logging.Formatter(f"[%(funcName)s]▶️ %(levelname)-8s | %(message)s")
    console_handler.setFormatter(console_formatter)

    # ✨ 【關鍵修正】：必須同時調低 Logger 本身的層級關卡
    verbose = False
    if verbose:
        logger.setLevel(logging.DEBUG)  # 讓 Logger 本身願意接收 DEBUG 訊息
        console_handler.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
        console_handler.setLevel(logging.INFO)
    # 🛡️ 螢幕防禦：不論全域開多大，螢幕上「永遠只印 INFO 以上」的日常報告，拒絕 DEBUG 碎碎念刷屏！
    logger.addHandler(console_handler)



    isp = RawImagePipeline()
    file_path = "/imageProcessig/image/arucoFailed1.nef"
    try:
        img_buffer = isp.load_image(file_path)

        tcc_finder = TCC_CARD_FINDER()
        tcc_finder.run(img_buffer)

        # QR code detection
        tcc_detected = tcc_finder.is_found()
        if tcc_detected:
            print(f'TCC card is found')
            pixels_mm = tcc_finder.get_pixels_mm()
            print(f'positioned, pixels/mm = {pixels_mm}')

            colorchecker_image = tcc_finder.get_colorchecker_image()
            tcc_finder.save("image/TCC.tiff")

    except Exception as e:
        print(f"Exception {e}")

    cv2.imshow("ArUco Detection Image", colorchecker_image)
    # 關鍵：必須加上這兩行，視窗才不會卡死或立刻消失
    cv2.waitKey(0)  # 等待使用者按下任意鍵
    cv2.destroyAllWindows()  # 關閉所有視窗