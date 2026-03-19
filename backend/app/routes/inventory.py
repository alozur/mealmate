from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import InventoryItem
from app.schemas import InventoryItemCreate, InventoryItemResponse, InventoryItemUpdate

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryItemResponse])
async def list_inventory(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(InventoryItem).order_by(InventoryItem.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=InventoryItemResponse, status_code=201)
async def create_inventory_item(
    body: InventoryItemCreate, db: AsyncSession = Depends(get_db)
):
    item = InventoryItem(
        name=body.name,
        quantity=body.quantity,
        unit=body.unit,
        category=body.category,
        storage_location=body.storage_location,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/{item_id}", response_model=InventoryItemResponse)
async def update_inventory_item(
    item_id: str, body: InventoryItemUpdate, db: AsyncSession = Depends(get_db)
):
    item = await db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_inventory_item(item_id: str, db: AsyncSession = Depends(get_db)):
    item = await db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    await db.delete(item)
    await db.commit()
