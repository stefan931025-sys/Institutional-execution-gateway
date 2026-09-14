import math
import logging

logger = logging.getLogger("InstitutionalGateway")

def normalize_order_constraints(price: float, qty: float, tick_size: float = 0.01, lot_size: float = 0.1) -> tuple:
    """
    Rounds price to the nearest valid tick size and quantity to the nearest lot size 
    to prevent exchange-side validation rejections.
    """
    try:
        normalized_price = round(round(price / tick_size) * tick_size, 5)
        normalized_qty = round(round(qty / lot_size) * lot_size, 2)
        
        logger.debug(f"Normalized price {price} -> {normalized_price} (Tick: {tick_size})")
        logger.debug(f"Normalized qty {qty} -> {normalized_qty} (Lot: {lot_size})")
        
        return normalized_price, normalized_qty
    except Exception as e:
        logger.error(f"Error normalizing order constraints: {e}")
        raise ValueError(f"Invalid price or quantity format: {e}")
