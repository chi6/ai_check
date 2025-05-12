from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..schemas.database_models import User, Subscription, SubscriptionPlan
from ..schemas.database_models import SUBSCRIPTION_STATUS_ACTIVE, PLAN_TYPE_SINGLE_USE, PLAN_TYPE_DAILY, PLAN_TYPE_MONTHLY

def check_user_usage_eligibility(db: Session, user_id: str) -> dict:
    """
    检查用户是否有资格使用检测服务
    
    返回格式:
    {
        "can_use": True/False,  # 是否可以使用
        "reason": "原因说明",    # 如果不能使用，说明原因
        "remaining_free_usage": 剩余免费次数,
        "active_subscription": 活跃订阅信息 (如果有)
    }
    """
    # 获取用户信息
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {
            "can_use": False,
            "reason": "用户不存在",
            "remaining_free_usage": 0
        }
    
    # 检查是否有活跃订阅
    active_subscription = get_active_subscription(db, user_id)
    if active_subscription:
        # 有活跃订阅，可以无限使用
        return {
            "can_use": True,
            "reason": "有活跃订阅",
            "remaining_free_usage": 0,
            "active_subscription": {
                "id": active_subscription.id,
                "plan_type": active_subscription.plan.plan_type,
                "plan_name": active_subscription.plan.name,
                "end_time": active_subscription.current_period_end
            }
        }
    
    # 检查剩余免费使用次数
    remaining_free_usage = user.free_usage_limit - user.usage_count
    if remaining_free_usage > 0:
        return {
            "can_use": True,
            "reason": "使用免费次数",
            "remaining_free_usage": remaining_free_usage
        }
    
    # 没有订阅且没有免费次数
    return {
        "can_use": False,
        "reason": "免费使用次数已用完，请购买或订阅",
        "remaining_free_usage": 0
    }

def increase_user_usage_count(db: Session, user_id: str) -> bool:
    """
    增加用户使用次数
    
    如果用户有活跃订阅，则不增加计数
    如果用户使用免费次数，则增加计数
    
    返回是否成功增加次数
    """
    # 检查是否有活跃订阅
    active_subscription = get_active_subscription(db, user_id)
    if active_subscription:
        # 有活跃订阅，不计数
        return True
    
    # 获取用户信息
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # 检查剩余免费使用次数
    remaining_free_usage = user.free_usage_limit - user.usage_count
    if remaining_free_usage <= 0:
        return False
    
    # 增加使用次数
    user.usage_count += 1
    db.commit()
    return True

def get_active_subscription(db: Session, user_id: str) -> Subscription:
    """
    获取用户的活跃订阅
    
    如果有多个活跃订阅，返回到期时间最晚的一个
    如果没有活跃订阅，返回None
    """
    now = datetime.now()
    
    # 查询用户的所有活跃订阅，按到期时间降序排序
    active_subscriptions = (
        db.query(Subscription)
        .join(SubscriptionPlan)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == SUBSCRIPTION_STATUS_ACTIVE,
            Subscription.current_period_end > now
        )
        .order_by(Subscription.current_period_end.desc())
        .all()
    )
    
    # 返回到期时间最晚的订阅，如果没有则返回None
    return active_subscriptions[0] if active_subscriptions else None

def add_usage_credits(db: Session, user_id: str, amount: int = 1) -> bool:
    """
    为用户添加使用次数额度
    
    参数:
    - user_id: 用户ID
    - amount: 要添加的次数，默认为1
    
    返回是否成功添加
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # 为用户账户添加使用额度（通过减少使用计数来实现）
    user.usage_count = max(0, user.usage_count - amount)
    db.commit()
    return True 