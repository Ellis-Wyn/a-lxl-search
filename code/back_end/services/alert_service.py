"""
=====================================================
预警服务
=====================================================

功能：
- 竞品退场预警
- 管线终止预警
- 新竞品预警
- 预警发送（日志/邮件/钉钉等）

使用方式：
    from services.alert_service import AlertService, AlertType

    alert_service = AlertService()
    alert = alert_service.create_discontinued_alert(pipeline_info)
    alert_service.send_alert(alert)
=====================================================
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)


# =====================================================
# 预警类型
# =====================================================

class AlertType(str, Enum):
    """预警类型"""
    COMPETITOR_WITHDRAWN = "competitor_withdrawn"  # 竞品退场
    PIPELINE_DISCONTINUED = "pipeline_discontinued"  # 管线终止
    NEW_COMPETITOR = "new_competitor"              # 新竞品
    PHASE_CHANGE = "phase_change"                  # 阶段变化
    CRAWLER_FAILURE = "crawler_failure"            # 爬虫失败
    CRAWLER_CONSECUTIVE_FAILURES = "crawler_consecutive_failures"  # 连续失败


class AlertSeverity(str, Enum):
    """预警级别"""
    HIGH = "high"       # 高危（如竞品退场）
    MEDIUM = "medium"   # 中等（如阶段变化）
    LOW = "low"        # 低（如信息更新）


# =====================================================
# 预警数据模型
# =====================================================

@dataclass
class Alert:
    """预警信息"""
    alert_type: AlertType
    company_name: str
    drug_code: str
    indication: str
    phase: str
    message: str
    severity: AlertSeverity
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_type": self.alert_type.value,
            "company_name": self.company_name,
            "drug_code": self.drug_code,
            "indication": self.indication,
            "phase": self.phase,
            "message": self.message,
            "severity": self.severity.value,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


# =====================================================
# 预警服务
# =====================================================

class AlertService:
    """预警服务"""

    def __init__(self):
        """初始化预警服务"""
        self.alerts: List[Alert] = []
        self.alert_handlers = []

        logger.info("AlertService initialized")

    def create_discontinued_alert(
        self,
        company_name: str,
        drug_code: str,
        indication: str,
        phase: str,
        reason: Optional[str] = None
    ) -> Alert:
        """
        创建终止预警

        Args:
            company_name: 公司名称
            drug_code: 药物代码
            indication: 适应症
            phase: 阶段
            reason: 终止原因

        Returns:
            Alert对象
        """
        message_parts = [
            f"⚠️ 竞品退场预警",
            f"公司: {company_name}",
            f"药物: {drug_code}",
            f"适应症: {indication}",
            f"阶段: {phase}",
        ]

        if reason:
            message_parts.append(f"原因: {reason}")

        message = " | ".join(message_parts)

        alert = Alert(
            alert_type=AlertType.COMPETITOR_WITHDRAWN,
            company_name=company_name,
            drug_code=drug_code,
            indication=indication,
            phase=phase,
            message=message,
            severity=AlertSeverity.HIGH,
            metadata={
                "reason": reason,
                "discontinued_at": datetime.utcnow().isoformat(),
            }
        )

        logger.info(f"Created discontinued alert for {drug_code}")
        return alert

    def create_new_pipeline_alert(
        self,
        company_name: str,
        drug_code: str,
        indication: str,
        phase: str,
        targets: List[str] = None
    ) -> Alert:
        """
        创建新管线预警

        Args:
            company_name: 公司名称
            drug_code: 药物代码
            indication: 适应症
            phase: 阶段
            targets: 靶点列表

        Returns:
            Alert对象
        """
        # 判断是否有重要靶点
        important_targets = ["PD-1", "PD-L1", "CTLA-4", "HER2", "EGFR", "ALK"]
        has_important_target = targets and any(t in important_targets for t in targets)

        severity = AlertSeverity.MEDIUM if has_important_target else AlertSeverity.LOW

        message = f"🆕 新竞品预警: {company_name} 的 {drug_code} ({phase}) 用于 {indication}"

        alert = Alert(
            alert_type=AlertType.NEW_COMPETITOR,
            company_name=company_name,
            drug_code=drug_code,
            indication=indication,
            phase=phase,
            message=message,
            severity=severity,
            metadata={
                "targets": targets or [],
                "has_important_target": has_important_target,
            }
        )

        logger.info(f"Created new pipeline alert for {drug_code}")
        return alert

    def create_phase_jump_alert(
        self,
        company_name: str,
        drug_code: str,
        old_phase: str,
        new_phase: str,
        indication: str = None
    ) -> Alert:
        """
        创建Phase Jump预警（阶段跳变）

        Args:
            company_name: 公司名称
            drug_code: 药物代码
            old_phase: 旧阶段
            new_phase: 新阶段
            indication: 适应症（可选）

        Returns:
            Alert对象
        """
        # 判断严重程度
        # Phase II → Phase III 是高危（接近上市）
        if "Phase 2" in old_phase and "Phase 3" in new_phase:
            severity = AlertSeverity.HIGH
        # Phase I → Phase II 是中等（进入关键临床）
        elif "Phase 1" in old_phase and "Phase 2" in new_phase:
            severity = AlertSeverity.MEDIUM
        # 其他Phase Jump是低危
        else:
            severity = AlertSeverity.LOW

        # 构建消息
        message_parts = [
            f"🚀 Phase Jump预警",
            f"公司: {company_name}",
            f"药物: {drug_code}",
            f"阶段: {old_phase} → {new_phase}",
        ]

        if indication:
            message_parts.append(f"适应症: {indication}")

        message = " | ".join(message_parts)

        alert = Alert(
            alert_type=AlertType.PHASE_CHANGE,
            company_name=company_name,
            drug_code=drug_code,
            indication=indication or "N/A",
            phase=new_phase,
            message=message,
            severity=severity,
            metadata={
                "old_phase": old_phase,
                "new_phase": new_phase,
                "phase_jump_type": f"{old_phase}_to_{new_phase}",
                "is_phase_2_to_3": "Phase 2" in old_phase and "Phase 3" in new_phase,
            }
        )

        logger.warning(
            f"Created phase jump alert for {drug_code}: "
            f"{old_phase} → {new_phase} ({severity.value})"
        )
        return alert

    def create_crawler_failure_alert(
        self,
        spider_name: str,
        consecutive_failures: int,
        last_error: str,
        last_failure_time: datetime,
        total_attempts: int = None
    ) -> Alert:
        """
        创建爬虫失败预警

        Args:
            spider_name: 爬虫名称
            consecutive_failures: 连续失败次数
            last_error: 最后一次错误信息
            last_failure_time: 最后失败时间
            total_attempts: 总尝试次数

        Returns:
            Alert对象
        """
        # 判断严重程度
        if consecutive_failures >= 5:
            severity = AlertSeverity.HIGH
        elif consecutive_failures >= 3:
            severity = AlertSeverity.MEDIUM
        else:
            severity = AlertSeverity.LOW

        message_parts = [
            f"⚠️ 爬虫失败预警",
            f"爬虫: {spider_name}",
            f"连续失败: {consecutive_failures} 次",
        ]

        if last_error:
            message_parts.append(f"最新错误: {last_error[:100]}")  # 限制长度

        if total_attempts:
            message_parts.append(f"总尝试次数: {total_attempts}")

        message = " | ".join(message_parts)

        alert = Alert(
            alert_type=AlertType.CRAWLER_CONSECUTIVE_FAILURES,
            company_name=spider_name,  # 使用spider_name作为company_name
            drug_code="N/A",  # 爬虫失败不涉及具体药物
            indication="crawler_failure",
            phase="N/A",
            message=message,
            severity=severity,
            metadata={
                "spider_name": spider_name,
                "consecutive_failures": consecutive_failures,
                "last_error": last_error,
                "last_failure_time": last_failure_time.isoformat(),
                "total_attempts": total_attempts,
            }
        )

        logger.warning(
            f"Created crawler failure alert for {spider_name} "
            f"(consecutive_failures={consecutive_failures}, severity={severity.value})"
        )
        return alert

    def send_alert(self, alert: Alert):
        """
        发送预警

        Args:
            alert: 预警对象
        """
        # 保存到内存
        self.alerts.append(alert)

        # 记录日志
        logger.warning(
            alert.message,
            extra={
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "company": alert.company_name,
                "drug_code": alert.drug_code,
            }
        )

        # 调用注册的处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

    def register_handler(self, handler_func):
        """
        注册预警处理器

        Args:
            handler_func: 处理函数，接收Alert对象
        """
        self.alert_handlers.append(handler_func)
        logger.info(f"Registered alert handler: {handler_func.__name__}")

    def get_alerts(
        self,
        alert_type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        获取预警列表

        Args:
            alert_type: 预警类型过滤
            severity: 严重程度过滤
            limit: 返回数量限制

        Returns:
            预警列表
        """
        filtered = self.alerts

        if alert_type:
            filtered = [a for a in filtered if a.alert_type == alert_type]

        if severity:
            filtered = [a for a in filtered if a.severity == severity]

        # 按时间倒序
        filtered = sorted(filtered, key=lambda a: a.created_at, reverse=True)

        return filtered[:limit]

    def get_recent_high_severity_alerts(self, hours: int = 24) -> List[Alert]:
        """
        获取最近的高危预警

        Args:
            hours: 最近N小时

        Returns:
            高危预警列表
        """
        from datetime import timedelta

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        recent_alerts = [
            a for a in self.alerts
            if a.created_at >= cutoff_time and a.severity == AlertSeverity.HIGH
        ]

        return sorted(recent_alerts, key=lambda a: a.created_at, reverse=True)

    def clear_alerts(self):
        """清空预警记录"""
        count = len(self.alerts)
        self.alerts.clear()
        logger.info(f"Cleared {count} alerts")


# =====================================================
# 预警处理器示例
# =====================================================

def email_alert_handler(alert: Alert):
    """邮件预警处理器（示例）"""
    # TODO: 实现邮件发送
    logger.info(f"[Email Handler] Would send email for alert: {alert.message}")


def dingtalk_alert_handler(alert: Alert):
    """钉钉预警处理器（示例）"""
    # TODO: 实现钉钉机器人
    logger.info(f"[DingTalk Handler] Would send DingTalk message for alert: {alert.message}")


# =====================================================
# 全局单例
# =====================================================

_default_alert_service: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    """
    获取AlertService单例

    Returns:
        AlertService实例
    """
    global _default_alert_service
    if _default_alert_service is None:
        _default_alert_service = AlertService()
    return _default_alert_service


__all__ = [
    "AlertType",
    "AlertSeverity",
    "Alert",
    "AlertService",
    "get_alert_service",
    "email_alert_handler",
    "dingtalk_alert_handler",
]
