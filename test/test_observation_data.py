"""
Test observation data processing and camera data handling.

This tests the critical data processing pipeline - ensuring observations
and camera data are properly parsed and processed.
"""

import numpy as np
import cv2
from unittest.mock import patch

from luckyrobots.core.models import ObservationModel, CameraData, CameraShape


class TestObservationData:
    """Test observation and camera data processing."""

    def test_observation_model_creation(self):
        """Test creating observation model with valid data."""
        observation_state = {
            "0": 0.5,
            "1": -1.0,
            "2": 1.5,
            "3": -0.5,
            "4": 0.0,
            "5": 1.0,
        }

        observation = ObservationModel(
            ObservationState=observation_state, ObservationCameras=None
        )

        assert observation.observation_state == observation_state
        assert observation.observation_cameras is None

    def test_observation_model_with_cameras(self):
        """Test observation model with camera data."""
        observation_state = {"shoulder_pan": 0.0}

        camera_data = CameraData(
            CameraName="test_camera",
            dtype="uint8",
            shape={"width": 640, "height": 480, "channel": 3},
            TimeStamp="2024-01-01T00:00:00Z",
            ImageData=b"test_image_data",
        )

        observation = ObservationModel(
            ObservationState=observation_state, ObservationCameras=[camera_data]
        )

        assert len(observation.observation_cameras) == 1
        assert observation.observation_cameras[0].camera_name == "test_camera"

    def test_camera_data_creation(self):
        """Test creating camera data with valid parameters."""
        camera = CameraData(
            CameraName="laptop",
            dtype="uint8",
            shape={"width": 640, "height": 480, "channel": 3},
            TimeStamp="2024-01-01T00:00:00Z",
            ImageData=b"mock_image_data",
        )

        assert camera.camera_name == "laptop"
        assert camera.dtype == "uint8"
        assert camera.shape["width"] == 640
        assert camera.shape["height"] == 480
        assert camera.shape["channel"] == 3
        assert camera.time_stamp == "2024-01-01T00:00:00Z"
        assert camera.image_data == b"mock_image_data"

    def test_camera_shape_model(self):
        """Test camera shape model."""
        shape = CameraShape(width=1920, height=1080, channel=3)

        assert shape.width == 1920
        assert shape.height == 1080
        assert shape.channel == 3

    @patch("cv2.imdecode")
    @patch("numpy.frombuffer")
    def test_camera_image_processing(self, mock_frombuffer, mock_imdecode):
        """Test camera image processing from bytes to numpy array."""
        # Mock image data
        mock_image_bytes = b"fake_jpeg_data"
        mock_numpy_array = np.array([1, 2, 3, 4], dtype=np.uint8)
        mock_decoded_image = np.zeros((480, 640, 3), dtype=np.uint8)

        mock_frombuffer.return_value = mock_numpy_array
        mock_imdecode.return_value = mock_decoded_image

        camera = CameraData(
            CameraName="test_camera",
            dtype="uint8",
            shape={"width": 640, "height": 480, "channel": 3},
            ImageData=mock_image_bytes,
        )

        # Process the image
        camera.process_image()

        # Verify the processing pipeline
        mock_frombuffer.assert_called_once_with(mock_image_bytes, np.uint8)
        mock_imdecode.assert_called_once_with(mock_numpy_array, cv2.IMREAD_COLOR)

        # Check that image_data is now the processed numpy array
        assert np.array_equal(camera.image_data, mock_decoded_image)

    def test_camera_image_processing_no_data(self):
        """Test camera image processing with no image data."""
        camera = CameraData(
            CameraName="test_camera",
            dtype="uint8",
            shape={"width": 640, "height": 480, "channel": 3},
            ImageData=None,
        )

        # Process should handle None gracefully
        result = camera.process_image()
        assert result is None
        assert camera.image_data is None

    @patch("cv2.imdecode")
    @patch("numpy.frombuffer")
    def test_observation_process_all_cameras(self, mock_frombuffer, mock_imdecode):
        """Test processing all cameras in an observation."""
        mock_numpy_array = np.array([1, 2, 3, 4], dtype=np.uint8)
        mock_decoded_image = np.zeros((480, 640, 3), dtype=np.uint8)

        mock_frombuffer.return_value = mock_numpy_array
        mock_imdecode.return_value = mock_decoded_image

        # Create observation with multiple cameras
        cameras = [
            CameraData(
                CameraName="camera1",
                dtype="uint8",
                shape={"width": 640, "height": 480, "channel": 3},
                ImageData=b"image1_data",
            ),
            CameraData(
                CameraName="camera2",
                dtype="uint8",
                shape={"width": 640, "height": 480, "channel": 3},
                ImageData=b"image2_data",
            ),
        ]

        observation = ObservationModel(
            ObservationState={"joint1": 0.0}, ObservationCameras=cameras
        )

        # Process all cameras
        observation.process_all_cameras()

        # Verify both cameras were processed
        assert mock_frombuffer.call_count == 2
        assert mock_imdecode.call_count == 2

        for camera in observation.observation_cameras:
            assert np.array_equal(camera.image_data, mock_decoded_image)

    def test_observation_process_no_cameras(self):
        """Test processing observation with no cameras."""
        observation = ObservationModel(
            ObservationState={"joint1": 0.0}, ObservationCameras=None
        )

        # Should handle None gracefully
        observation.process_all_cameras()
        assert observation.observation_cameras is None

    def test_camera_data_alias_fields(self):
        """Test that camera data handles alias fields correctly."""
        # Test with alias field names
        camera_dict = {
            "CameraName": "test_camera",
            "dtype": "uint8",
            "shape": {"width": 640, "height": 480, "channel": 3},
            "TimeStamp": "2024-01-01T00:00:00Z",
            "ImageData": b"test_data",
        }

        camera = CameraData(**camera_dict)

        assert camera.camera_name == "test_camera"
        assert camera.time_stamp == "2024-01-01T00:00:00Z"
        assert camera.image_data == b"test_data"

    def test_observation_model_alias_fields(self):
        """Test that observation model handles alias fields correctly."""
        # Test with alias field names
        obs_dict = {
            "ObservationState": {"joint1": 1.0},
            "ObservationCameras": [
                {
                    "CameraName": "test_camera",
                    "dtype": "uint8",
                    "shape": {"width": 640, "height": 480, "channel": 3},
                }
            ],
        }

        observation = ObservationModel(**obs_dict)

        assert observation.observation_state == {"joint1": 1.0}
        assert len(observation.observation_cameras) == 1
        assert observation.observation_cameras[0].camera_name == "test_camera"

    def test_actuator_state_values(self):
        """Test different actuator state configurations."""
        # Test so100 robot configuration
        so100_state = {"0": 1.0, "1": -2.0, "2": 2.5, "3": -1.0, "4": 0.5, "5": 1.5}

        observation = ObservationModel(ObservationState=so100_state)

        # Verify all actuators are present
        expected_actuators = ["0", "1", "2", "3", "4", "5"]

        for actuator in expected_actuators:
            assert actuator in observation.observation_state

        # Test actuator limits (values should be within expected ranges)
        assert -2.2 <= observation.observation_state["0"] <= 2.2
        assert -3.14158 <= observation.observation_state["1"] <= 0.2
        assert 0.0 <= observation.observation_state["2"] <= 3.14158
        assert -2.0 <= observation.observation_state["3"] <= 1.8
        assert -3.14158 <= observation.observation_state["4"] <= 3.14158
        assert -0.2 <= observation.observation_state["5"] <= 2.0
