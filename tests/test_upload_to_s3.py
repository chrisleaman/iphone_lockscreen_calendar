"""
Tests for S3 upload functionality
"""
import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import upload_to_s3, config


class TestUploadToS3:
    """Test cases for upload_to_s3 function"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create a temporary test image file
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        self.temp_file.write(b'fake image data')
        self.temp_file.close()
        self.test_image_path = self.temp_file.name

    def teardown_method(self):
        """Clean up test fixtures"""
        # Remove temporary file
        if os.path.exists(self.test_image_path):
            os.unlink(self.test_image_path)

    def test_file_not_found(self):
        """Test behavior when file doesn't exist"""
        result = upload_to_s3("nonexistent_file.jpg")
        assert result is False

    @mock_aws
    def test_successful_upload(self):
        """Test successful S3 upload"""
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = config["aws"]["bucket_name"]
        s3_client.create_bucket(Bucket=bucket_name)

        # Test upload
        result = upload_to_s3(self.test_image_path, "test_image.jpg")
        assert result is True

        # Verify file was uploaded
        objects = s3_client.list_objects_v2(Bucket=bucket_name)
        assert 'Contents' in objects
        assert len(objects['Contents']) == 1
        assert objects['Contents'][0]['Key'] == 'test_image.jpg'

    @mock_aws
    def test_bucket_not_exists(self):
        """Test behavior when S3 bucket doesn't exist"""
        # Don't create the bucket - it should fail
        result = upload_to_s3(self.test_image_path, "test_image.jpg")
        assert result is False

    def test_no_credentials(self):
        """Test behavior when AWS credentials are missing"""
        # Temporarily remove AWS credentials from environment
        with patch.dict(os.environ, {}, clear=True):
            with patch('main.AWS_ACCESS_KEY_ID', ''), \
                 patch('main.AWS_SECRET_ACCESS_KEY', ''):
                result = upload_to_s3(self.test_image_path, "test_image.jpg")
                assert result is False

    @mock_aws
    def test_access_denied(self):
        """Test behavior when access is denied"""
        # Create bucket but test with invalid credentials
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = config["aws"]["bucket_name"]
        s3_client.create_bucket(Bucket=bucket_name)

        # Mock ClientError for access denied
        with patch('boto3.client') as mock_boto_client:
            mock_s3_client = MagicMock()
            mock_boto_client.return_value = mock_s3_client

            # Configure the mock to raise AccessDenied error
            error_response = {
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': 'Access Denied'
                }
            }
            mock_s3_client.upload_file.side_effect = ClientError(error_response, 'upload_file')

            result = upload_to_s3(self.test_image_path, "test_image.jpg")
            assert result is False

    @mock_aws
    def test_default_image_name(self):
        """Test upload with default image name"""
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = config["aws"]["bucket_name"]
        s3_client.create_bucket(Bucket=bucket_name)

        # Test upload without specifying image name
        result = upload_to_s3(self.test_image_path)
        assert result is True

        # Verify file was uploaded with default name
        objects = s3_client.list_objects_v2(Bucket=bucket_name)
        assert 'Contents' in objects
        assert objects['Contents'][0]['Key'] == 'lockscreen.jpg'

    @mock_aws
    def test_upload_content_type(self):
        """Test that correct content type is set"""
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = config["aws"]["bucket_name"]
        s3_client.create_bucket(Bucket=bucket_name)

        # Test upload
        result = upload_to_s3(self.test_image_path, "test_image.jpg")
        assert result is True

        # Get object metadata to check content type
        response = s3_client.head_object(Bucket=bucket_name, Key='test_image.jpg')
        assert response['ContentType'] == 'image/jpeg'

    def test_general_exception(self):
        """Test behavior when a general exception occurs"""
        # Mock boto3.client to raise a general exception
        with patch('boto3.client', side_effect=Exception("Mock exception")):
            result = upload_to_s3(self.test_image_path, "test_image.jpg")
            assert result is False


class TestUploadIntegration:
    """Integration tests for S3 upload in context of main application"""

    @mock_aws
    def test_upload_generated_lockscreen(self):
        """Test uploading an actual generated lockscreen image"""
        # This test would require generating a real lockscreen image
        # For now, we'll test with a mock image file

        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = config["aws"]["bucket_name"]
        s3_client.create_bucket(Bucket=bucket_name)

        # Create a temporary image file that simulates lockscreen output
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(b'mock lockscreen image data')
            temp_image_path = temp_file.name

        try:
            # Test upload
            result = upload_to_s3(temp_image_path, "daily_lockscreen.jpg")
            assert result is True

            # Verify the upload
            objects = s3_client.list_objects_v2(Bucket=bucket_name)
            assert 'Contents' in objects
            uploaded_object = objects['Contents'][0]
            assert uploaded_object['Key'] == 'daily_lockscreen.jpg'
            assert uploaded_object['Size'] > 0

        finally:
            # Clean up
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)


if __name__ == "__main__":
    pytest.main([__file__])