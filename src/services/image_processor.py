import base64
import io
from PIL import Image
from typing import Optional, Tuple


class ImageProcessor:
    def __init__(self, max_size: Tuple[int, int] = (1920, 1080)):
        self.max_size = max_size
    
    def load_image(self, image_path: str) -> Image.Image:
        """Load image from file path"""
        return Image.open(image_path)
    
    def image_to_base64(self, image: Image.Image, format: str = "PNG") -> str:
        """Convert PIL Image to base64 string"""
        
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)
        
        return base64.b64encode(buffer.read()).decode("utf-8")
    
    def base64_to_image(self, image_base64: str) -> Image.Image:
        """Convert base64 string to PIL Image"""
        
        image_bytes = base64.b64decode(image_base64)
        buffer = io.BytesIO(image_bytes)
        
        return Image.open(buffer)
    
    def file_to_base64(self, file_path: str) -> str:
        """Load image file and convert to base64"""
        
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def resize_for_bedrock(self, image: Image.Image) -> Image.Image:
        """Resize image if needed for Bedrock (max 3.75MB, recommended < 1568px)"""
        
        # Nova Pro works best with images under 1568px on longest side
        max_dimension = 1568
        
        width, height = image.size
        
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def prepare_for_bedrock(self, image_path: str) -> str:
        """Load, resize if needed, and convert to base64 for Bedrock"""
        
        image = self.load_image(image_path)
        image = self.resize_for_bedrock(image)
        
        # Convert to RGB if necessary (remove alpha channel)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        return self.image_to_base64(image, format="PNG")
    
    def get_image_info(self, image: Image.Image) -> dict:
        """Get image metadata"""
        
        return {
            "width": image.size[0],
            "height": image.size[1],
            "mode": image.mode,
            "format": image.format
        }
    
    def bytes_to_base64(self, image_bytes: bytes) -> str:
        """Convert raw image bytes to base64"""
        return base64.b64encode(image_bytes).decode("utf-8")
    
    def create_test_image(self, width: int = 800, height: int = 600) -> Image.Image:
        """Create a simple test image"""
        
        # Create a simple gradient image for testing
        image = Image.new("RGB", (width, height), color=(73, 109, 137))
        return image