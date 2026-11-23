# -*- encoding: utf-8 -*-

import os
import tempfile
from io import BytesIO

from PIL import Image, ImageCms
import rawpy
import imageio.v3 as iio

from lrprev import LRPrevFileWriter


class ThumbBuilder:
    """
    Build thumbnails from original source
    """

    DEFAULT_LEVELS = [1920, 960, 480, 240, 120, 60]

    def __init__(self, prevfile: LRPrevFileWriter):
        self.lrprev = prevfile
        self.exts = Image.registered_extensions().keys()

    def convert_to_srgb(self, img):
        """Convert PIL image to sRGB color space (if possible)"""
        icc = img.info.get("icc_profile", "")
        if icc:
            io_handle = BytesIO(icc)  # virtual file
            src_profile = ImageCms.ImageCmsProfile(io_handle)
            dst_profile = ImageCms.createProfile("sRGB")
            img = ImageCms.profileToProfile(img, src_profile, dst_profile)
        return img

    def build_thumbs(self, fname: str, level_sizes: list[int] = None, orientation=None):
        """
        build thumbs and add them to a prevfile

        :param level_size: array of sizes sorted from largest to lowest
        :param orientation : image orientation. Image in root_pixels/db or in lrprev files are not "User oriented" :
            the orientation is the raw camera output orientation
            If source file is a jpeg file "user oriented", we need to reorient as camera output
        """
        if level_sizes is None:
            level_sizes = self.DEFAULT_LEVELS

        # process standard or raw image
        _, ext = os.path.splitext(fname)
        if ext.lower() in self.exts:
            image = Image.open(fname)
        else:
            _, temp_path = tempfile.mkstemp(suffix=".jpeg")
            with rawpy.imread(fname) as raw:
                rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=False)
            iio.imwrite(temp_path, rgb)
            image = Image.open(temp_path)

        if orientation == "AB":
            pass
        elif orientation == "BA":
            # exif orientation = 2 : vertical mirror
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif orientation == "CD":
            # exif orientation = 3 : rotation 180°
            image = image.transpose(Image.Transpose.ROTATE_180)
        elif orientation == "DC":
            # exif orientation = 4 : horizontal mirror
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        elif orientation == "CB":
            # exif orientation = 5 : horizontal mirror + rotation 90° CCW
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).transpose(
                Image.Transpose.ROTATE_270
            )
        elif orientation == "BC":
            # exif orientation = 6 : rotation 270° CCW
            image = image.transpose(Image.Transpose.ROTATE_90)
        elif orientation == "AD":
            # exif orientation = 7 :  horizontal mirror + rotation 270° CCW
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).transpose(
                Image.Transpose.ROTATE_90
            )
        elif orientation == "DA":
            # exif orientation = 8 : rotation 90° CCW
            image = image.transpose(Image.Transpose.ROTATE_270)

        image = self.convert_to_srgb(image)

        # TODO when size < 1920

        for size in level_sizes:
            # Define the thumbnail size as a tuple (width, height)
            thumbnail_size = (size, size)

            # Create a thumbnail
            image.thumbnail(thumbnail_size, resample=Image.Resampling.BOX)
            buffer = BytesIO()
            image.save(buffer, format="jpeg", quality=70)
            self.lrprev.add_thumb(image.width, image.height, buffer.getvalue())
