
import os

job_name = "painter_vit_large"
ckpt_file = "painter_vit_large.pth"
prompt = "000000000165_box0"

image_dir = f'../../models_inference/{job_name}/coco_pose_inference_{ckpt_file}_{prompt}/'
if image_dir[-1] != "/":
    image_dir += '/'
print(image_dir)


_base_ = [
    './_base_/default_runtime.py',
    './_base_/coco.py'
]
evaluation = dict(interval=10, metric='mAP', save_best='AP')

optimizer = dict(
    type='Adam',
    lr=5e-4,
)
optimizer_config = dict(grad_clip=None)
# learning policy
lr_config = dict(
    policy='step',
    warmup='linear',
    warmup_iters=500,
    warmup_ratio=0.001,
    step=[170, 200])
total_epochs = 210
channel_cfg = dict(
    num_output_channels=17,
    dataset_joints=17,
    dataset_channel=[
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
    ],
    inference_channel=[
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
    ])

# fake model settings
model = dict(
    type='TopDownCustom',
    pretrained=None,
    backbone=dict(
        type='HRNet',
        in_channels=3,
        extra=dict(
            stage1=dict(
                num_modules=1,
                num_branches=1,
                block='BOTTLENECK',
                num_blocks=(4,),
                num_channels=(64,),
            ),
            stage2=dict(
                num_modules=1,
                num_branches=2,
                block='BASIC',
                num_blocks=(4, 4),
                num_channels=(32, 64),
            ),
            stage3=dict(
                num_modules=4,
                num_branches=3,
                block='BASIC',
                num_blocks=(4, 4, 4),
                num_channels=(32, 64, 128),
            ),
            stage4=dict(
                num_modules=3,
                num_branches=4,
                block='BASIC',
                num_blocks=(4, 4, 4, 4),
                num_channels=(32, 64, 128, 256),
            ),
        ),
    ),
    keypoint_head=dict(
        type='TopdownHeatmapSimpleHead',
        in_channels=32,
        out_channels=channel_cfg['num_output_channels'],
        num_deconv_layers=0,
        extra=dict(
            final_conv_kernel=1,
        ),
        loss_keypoint=dict(type='JointsMSELoss', use_target_weight=True),
    ),
    train_cfg={},
    test_cfg=dict(
        flip_test=True,
        post_process='default',
        shift_heatmap=True,
        modulate_kernel=17,
    ),
)

data_cfg = dict(
    image_size=[192, 256],
    heatmap_size=[192, 256],
    # heatmap_size=[48, 64],
    # image_size=[640, 320],  # w, h
    # heatmap_size=[640, 320],
    num_output_channels=channel_cfg['num_output_channels'],
    num_joints=channel_cfg['dataset_joints'],
    dataset_channel=channel_cfg['dataset_channel'],
    inference_channel=channel_cfg['inference_channel'],
    soft_nms=False,
    nms_thr=1.0,
    oks_thr=0.9,
    vis_thr=0.2,
    use_gt_bbox=False,
    imagename_with_boxid=True,  # custom
    det_bbox_thr=0.0,
    bbox_file='../../datasets/coco_pose/person_detection_results/'
    'COCO_val2017_detections_AP_H_56_person.json',
)


# sigma = [1.5, 3]  # 2
sigma = 3  # use the hyper params of R, which is heatmap

val_pipeline = [
    dict(type='LoadImageFromFile'),  # load custom images according to filename and box_id, using topdown_coco_dataset
    dict(type='TopDownGetBboxCenterScale', padding=1.25),
    dict(
        type='Collect',
        keys=['img'],
        meta_keys=[
            'image_file', 'center', 'scale', 'rotation', 'bbox_score',
            'flip_pairs'
        ]),
]

test_pipeline = val_pipeline

data_root = '../../datasets/coco'
data = dict(
    samples_per_gpu=32,
    workers_per_gpu=8,
    val_dataloader=dict(samples_per_gpu=32),
    test_dataloader=dict(samples_per_gpu=32),
    pseudo_test=True,  # custom arg
    val=dict(
        type='TopDownCocoDatasetCustom',
        ann_file=f'{data_root}/annotations/person_keypoints_val2017.json',
        # img_prefix=f'{data_root}/val2017/',
        img_prefix=image_dir,
        data_cfg=data_cfg,
        pipeline=val_pipeline,
        dataset_info={{_base_.dataset_info}}),
    test=dict(
        type='TopDownCocoDatasetCustom',
        ann_file=f'{data_root}/annotations/person_keypoints_val2017.json',
        # img_prefix=f'{data_root}/val2017/',
        img_prefix=image_dir,
        data_cfg=data_cfg,
        pipeline=test_pipeline,
        dataset_info={{_base_.dataset_info}}),
)

# import newly registered module
custom_imports = dict(
    imports=[
        'model.top_down',
        'data.topdown_coco_dataset',
        'data.pipelines.top_down_transform',
    ],
    allow_failed_imports=False)
