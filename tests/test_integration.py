import pytest
from httpx import AsyncClient
from app.main import app
from app.models.product import DifficultyLevel

@pytest.mark.asyncio
async def test_admin_stats_unauthorized():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/admin/stats")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_product_extra_fields():
    # This is a unit-like test for the schema/model logic
    from app.routers.products import ProductCreate
    
    payload = {
        "title": "Digital Pattern",
        "description": "A cool pattern",
        "price": 5.0,
        "category": "patterns",
        "is_digital": True,
        "difficulty_level": "intermediate",
        "file_url": "https://example.com/pattern.pdf"
    }
    
    product_data = ProductCreate(**payload)
    assert product_data.is_digital is True
    assert product_data.difficulty_level == DifficultyLevel.intermediate
