# AUTOGENERATED! DO NOT EDIT! File to edit: 00_utils.ipynb (unless otherwise specified).

__all__ = ['sedas_client', 'sedas_get_collections', 'sedas_find_datasets', 'sedas_download', 'sedas_extract',
           'convert2cog', 'mosaic2cog', 's3_create_client', 'gb', 's3_single_upload', 'get_rel_dir_s3_paths',
           's3_upload_dir', 's3_list_objects_paths', 's3_list_objects']

# Cell
import os
import zipfile

import boto3

from sedas_pyapi.sedas_api import SeDASAPI

# Cell
def sedas_client():
    "Log into sedas api."
    sedas = SeDASAPI(os.getenv('SEDAS_USERNAME'), os.getenv('SEDAS_PWD'))
    sedas.base_url="https://geobrowsertest.satapps.org/api/"
    return sedas

# Cell
def sedas_get_collections():
    sedas = sedas_client()
    result_groups = sedas.list_sensor_groups()
    groups = []
    for i in range(0, len(result_groups)):
        groups.append(result_groups[i]['name'])
    return f"Available groups are: {', '.join(groups)}"

# Cell
def sedas_find_datasets(wkt, startDate, endDate, collection):
    optical_groups = ['S2','Pleiades','SPOT']
    sar_groups = ['S1','Cosmo-SkyMed','AIRSAR']
    sedas = sedas_client()
    if collection in optical_groups:
        res = sedas.search_optical(wkt, startDate, endDate, source_group=collection)
    elif collection in sar_groups:
        res = sedas.search_sar(wkt, startDate, endDate, source_group=collection)
    return res

# Cell
def sedas_download(sedas_res_dict, down_zip, sedas=None):
    "Use product dict to download product zip."
    if not sedas:
        sedas = sedas_client()
    sedas.download(sedas_res_dict, down_zip)

# Cell
def sedas_extract(down_zip, scene_dir):
    with zipfile.ZipFile(down_zip, 'r') as zip_ref:
        zip_ref.extractall(scene_dir)
    if os.path.exists(scene_dir):
        os.remove(down_zip)

# Cell
def convert2cog(img_path, cog_path, band):
    """
    Convert gdal raster into COG with default settings.
    Considering lzw compression.
    See https://www.cogeo.org/developers-guide.html.
    """
    # translate into new cog file
    kwargs = {
        'format': 'COG',
#         'creationOptions' : ['COMPRESS=LZW'],
        'bandList': [band]
    }
    ds = gdal.Translate(cog_path, img_path, **kwargs)
    ds = None
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} Conversion complete: {os.path.exists(cog_path)}.")

# Cell
def mosaic2cog(imgs, out_cog, band):
    """
    Mosaic imgs into cog.
    Usual vrt assumptions.
    """
#     out_cog_mosaic = f"{imgs[0][:-13]}_band{band}.TIF"
    tmp_vrt = f"{out_cog[:-4]}_mosaic.tif"

    # mosaic into vrt
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} Mosaicing band {band} imgs: {imgs}")
    ds = gdal.BuildVRT(tmp_vrt, imgs, bandList=[band])

    # convert write vrt mosaic to cog
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} Converting band {band} mosaic {tmp_vrt} to COG {out_cog_mosaic}")
    convert2cog(ds, out_cog_mosaic, 1)
    ds = None

    if os.path.exists(tmp_vrt):
        os.remove(tmp_vrt)

# Cell
def s3_create_client(s3_bucket):
    """
    Create and set up a connection to S3
    :param s3_bucket:
    :return: the s3 client object.
    """
    access = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")

    session = boto3.Session(
        access,
        secret,
    )
    endpoint_url = os.getenv("AWS_S3_ENDPOINT_URL")

    if endpoint_url is not None:
        s3 = session.resource('s3', endpoint_url=endpoint_url)
    else:
        s3 = session.resource('s3', region_name='eu-west-2')

    bucket = s3.Bucket(s3_bucket)

    if endpoint_url is not None:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access,
            aws_secret_access_key=secret,
            endpoint_url=endpoint_url
        )
    else:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access,
            aws_secret_access_key=secret
        )
    return s3_client, bucket

# Cell
gb = 1024 ** 3

# Cell
def s3_single_upload(in_path, s3_path, s3_bucket):
    """
    put a file into S3 from the local file system.
    :param in_path: a path to a file on the local file system
    :param s3_path: where in S3 to put the file.
    :return: None
    """
    # prep session & creds
    s3_client, bucket = s3_create_client(s3_bucket)

    # Ensure that multipart uploads only happen if the size of a transfer is larger than
    # S3's size limit for non multipart uploads, which is 5 GB. we copy using multipart
    # at anything over 4gb
    transfer_config = boto3.s3.transfer.TransferConfig(multipart_threshold=2 * gb,
                                                       max_concurrency=10,
                                                       multipart_chunksize=2 * gb,
                                                       use_threads=True)
    s3_client.upload_file(in_path, bucket.name, s3_path)

# Cell
def get_rel_dir_s3_paths(local_dir, s3_dir):
    """
    returns local path, remote path pair list.
    """
    paths = []
    for subdir, dirs, files in os.walk(local_dir):
        for file in files:
            full_path = os.path.join(subdir, file)
            paths.append([ full_path, s3_dir + full_path[len(local_dir):] ])
    return paths

# Cell
def s3_upload_dir(in_dir, s3_bucket, s3_dir):

    paths = get_rel_dir_s3_paths(in_dir, s3_dir)

    upload_list = [(in_path, out_path, s3_bucket)
                   for in_path, out_path in paths]

    for i in upload_list:
        s3_single_upload(i[0], i[1], i[2])

# Cell
def s3_list_objects_paths(s3_bucket, prefix):
    """List of paths only returned, not full object responses"""
    client, bucket = s3_create_client(s3_bucket)

    return [e['Key'] for p in client.get_paginator("list_objects_v2").paginate(Bucket=s3_bucket, Prefix=prefix) for e in p['Contents']]


# Cell
def s3_list_objects(s3_bucket, prefix):
    # prep session & creds
    client, bucket = s3_create_client(s3_bucket)
    response = client.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)

    return response