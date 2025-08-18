import mediapipe as mp
import json
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

def generate_keypoints_json(image_path, output_path):
    # 🔹 Load the Pose Landmarker model
    model_path = "app/static/app/models/pose_landmarker_full.task"
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(base_options=base_options,output_segmentation_masks=False)
    detector = vision.PoseLandmarker.create_from_options(options)

    # 🔹 Load image
    image = mp.Image.create_from_file(image_path)

    # 🔹 Run pose detection
    result = detector.detect(image)
    if not result.pose_landmarks:
        raise ValueError("No pose landmarks detected.")

    # 🔹 Extract keypoints
    keypoints_flat = []
    for landmark in result.pose_landmarks[0]:
        keypoints_flat.extend([landmark.x, landmark.y, landmark.visibility])

    openpose_format = {
        "people": [
            {
                "pose_keypoints_2d": keypoints_flat
            }
        ]
    }

    # 🔹 Save to JSON
    with open(output_path, 'w') as f:
        json.dump(openpose_format, f, indent=2)

    print(f"[Keypoints] OpenPose-style JSON saved to: {output_path}")

