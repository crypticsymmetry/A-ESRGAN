import argparse
import cv2
import glob
import os
from basicsr.archs.rrdbnet_arch import RRDBNet

from aesrgan import RealESRGANer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, default='.\inputs', help='Input image or folder')
    parser.add_argument(
        '--model_path',
        type=str,
        default='experiments/pretrained_models/A_ESRGAN_Single.pth',
        help='Path to the pre-trained model')
    parser.add_argument('--output', type=str, default='results', help='Output folder')
    parser.add_argument('--suffix', type=str, default='', help='Suffix of the restored image')
    parser.add_argument('--tile', type=int, default=0, help='Tile size, 0 for no tile during testing')
    parser.add_argument('--tile_pad', type=int, default=10, help='Tile padding')
    parser.add_argument('--pre_pad', type=int, default=0, help='Pre padding size at each border')
    parser.add_argument('--half', action='store_true', help='Use half precision during inference')
    parser.add_argument('--block', type=int, default=23, help='num_block in RRDB')
    parser.add_argument('--netscale', type=int, default=4, help='netscale value')
    parser.add_argument('--outscale', type=int, default=2, help='Output folder')
    parser.add_argument('--face_enhance', action='store_true', help='Use GFPGAN to enhance face')
    parser.add_argument(
        '--ext',
        type=str,
        default='auto',
        help='Image extension. Options: auto | jpg | png, auto means using the same extension as inputs')
    args = parser.parse_args()
    netscale = args.netscale
    outscale = args.outscale

    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=args.block, num_grow_ch=32, scale=netscale)

    upsampler = RealESRGANer(
        scale=netscale,
        model_path=args.model_path,
        model=model,
        tile=args.tile,
        tile_pad=args.tile_pad,
        pre_pad=args.pre_pad,
        half=args.half)

    if args.face_enhance:  # Use GFPGAN for face enhancement
        from gfpgan import GFPGANer
        face_enhancer = GFPGANer(
            model_path='https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth',
            upscale=args.outscale,
            arch='clean',
            channel_multiplier=2,
            bg_upsampler=upsampler)
    os.makedirs(args.output, exist_ok=True)


    if os.path.isfile(args.input):
        paths = [args.input]
    else:
        paths = sorted(glob.glob(os.path.join(args.input, '*')))

    for idx, path in enumerate(paths):
        imgname, extension = os.path.splitext(os.path.basename(path))
        print('Testing', idx, imgname)

        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if len(img.shape) == 3 and img.shape[2] == 4:
            img_mode = 'RGBA'
        else:
            img_mode = None

        try:
            if args.face_enhance:
                _, _, output = face_enhancer.enhance(img, has_aligned=False, only_center_face=True, paste_back=True)
            else:
                output, _ = upsampler.enhance(img, outscale=outscale)
        except Exception as error:
            print('Error', error)
            print('If you encounter CUDA out of memory, try to set --tile with a smaller number.')
        else:
            if args.ext == 'auto':
                extension = extension[1:]
            else:
                extension = args.ext
            if img_mode == 'RGBA':  # RGBA images should be saved in png format
                extension = 'png'
            save_path = os.path.join(args.output, f'{imgname}.{extension}')
            cv2.imwrite(save_path, output)


if __name__ == '__main__':
    main()
