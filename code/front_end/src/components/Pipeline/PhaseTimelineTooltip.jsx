/**
 * ============================================================
 * PhaseTimelineTooltip Component
 * ============================================================
 *
 * 管线时间线悬停提示组件
 *
 * 功能：
 * - 鼠标悬停300ms后显示时间线
 * - 懒加载历史数据
 * - 自动清理资源
 *
 * 使用方式：
 *   <PhaseTimelineTooltip pipelineId="xxx-xxx">
 *     <span>Phase III ⏱</span>
 *   </PhaseTimelineTooltip>
 *
 * 作者：A_lxl_search Team
 * 创建日期：2026-03-12
 * ============================================================
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { pipelineHistoryApi } from '../../api';

// =====================================================
// 常量定义
// =====================================================

const HOVER_DELAY_MS = 300;
const PHASE_NAME_MAP = {
  'I': 'I期',
  'II': 'II期',
  'III': 'III期',
  'Approved': '已批准',
  'preclinical': '临床前',
  'Phase I': 'I期',
  'Phase II': 'II期',
  'Phase III': 'III期',
};

// =====================================================
// 工具函数
// =====================================================

/**
 * 格式化阶段名称为中文
 */
const formatPhaseName = (phase) => {
  if (!phase) return '未知';
  return PHASE_NAME_MAP[phase] || phase.replace(/^Phase\s*/, '') + '期';
};

/**
 * 格式化持续时间
 */
const formatDuration = (days) => {
  if (!days) return '';
  if (days < 30) return `${days}天`;
  if (days < 365) return `${Math.floor(days / 30)}个月`;
  return `${Math.floor(days / 365)}年`;
};

// =====================================================
// 主组件
// =====================================================

export default function PhaseTimelineTooltip({ pipelineId, children }) {
  // =====================================================
  // State
  // =====================================================
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isVisible, setIsVisible] = useState(false);

  // =====================================================
  // Refs
  // =====================================================
  const timeoutRef = useRef(null);
  const abortControllerRef = useRef(null);

  // =====================================================
  // Effects
  // =====================================================

  /**
   * 组件卸载时清理资源
   */
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // =====================================================
  // Callbacks
  // =====================================================

  /**
   * 获取时间线数据
   */
  const fetchTimeline = useCallback(async () => {
    if (!pipelineId) {
      setError(new Error('缺少 pipelineId'));
      return;
    }

    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();

    try {
      setLoading(true);
      setError(null);
      const data = await pipelineHistoryApi.getSummary(pipelineId);
      setTimeline(data);
    } catch (err) {
      // 忽略取消请求的错误
      if (err.name !== 'AbortError') {
        setError(err);
        console.error('[PhaseTimelineTooltip] Failed to load timeline:', err);
      }
    } finally {
      setLoading(false);
    }
  }, [pipelineId]);

  /**
   * 鼠标进入处理
   */
  const handleMouseEnter = useCallback(() => {
    // 清除之前的定时器
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // 延迟显示
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);

      // 如果还没加载过数据，则加载
      if (!timeline && !loading && !error) {
        fetchTimeline();
      }
    }, HOVER_DELAY_MS);
  }, [timeline, loading, error, fetchTimeline]);

  /**
   * 鼠标离开处理
   */
  const handleMouseLeave = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsVisible(false);
  }, []);

  // =====================================================
  // Render Helpers
  // =====================================================

  /**
   * 渲染加载状态
   */
  const renderLoading = () => (
    <div className="flex items-center gap-2 py-2">
      <div className="w-3 h-3 border border-[#00ff88] border-t-transparent rounded-full animate-spin" />
      <span className="font-['JetBrains_Mono'] text-xs text-[#666]">加载中...</span>
    </div>
  );

  /**
   * 渲染错误状态
   */
  const renderError = () => (
    <div className="font-['Source_Sans_3'] text-xs text-[#666] py-1">
      暂无历史记录
    </div>
  );

  /**
   * 渲染空状态
   */
  const renderEmpty = () => (
    <div className="font-['Source_Sans_3'] text-xs text-[#666] py-1">
      暂无历史记录
    </div>
  );

  /**
   * 渲染时间线列表
   */
  const renderTimeline = () => {
    if (!timeline?.timeline?.length) {
      return renderEmpty();
    }

    return (
      <div className="space-y-2">
        {timeline.timeline.map((item, index) => (
          <div key={`${item.phase}-${item.date}`} className="flex items-center gap-2">
            {/* 阶段点 */}
            <div
              className={`w-2 h-2 rounded-full flex-shrink-0 ${
                item.is_current ? 'bg-[#00ff88] shadow-[0_0_8px_rgba(0,255,136,0.5)]' : 'bg-[#444]'
              }`}
            />

            {/* 阶段信息 */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="font-['Source_Sans_3'] text-xs text-[#e0e0e0] truncate">
                  {formatPhaseName(item.phase)}
                </span>
                <span className="font-['JetBrains_Mono'] text-xs text-[#666] flex-shrink-0">
                  {item.date}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  /**
   * 渲染内容
   */
  const renderContent = () => {
    if (loading) {
      return renderLoading();
    }

    if (error || !timeline) {
      return renderError();
    }

    return (
      <>
        {/* 标题 */}
        <div className="font-['JetBrains_Mono'] text-xs text-[#00ff88] mb-2 truncate">
          {timeline.drug_code} 研发历程
        </div>

        {/* 时间线 */}
        {renderTimeline()}

        {/* 底部统计 */}
        {timeline.total_days_active && (
          <div className="mt-2 pt-2 border-t border-[#333]">
            <span className="font-['JetBrains_Mono'] text-xs text-[#666]">
              累计 {formatDuration(timeline.total_days_active)} ({timeline.total_days_active}天)
            </span>
          </div>
        )}
      </>
    );
  };

  // =====================================================
  // 主渲染
  // =====================================================

  return (
    <div
      className="relative inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}

      {/* Tooltip */}
      {isVisible && (
        <div className="absolute left-full top-0 ml-2 z-50 w-64 pointer-events-none">
          <div className="bg-[#1a1a1a] border border-[#333] rounded-lg shadow-xl p-3">
            {renderContent()}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * PropTypes 定义（如果使用 prop-types）
 */
// PhaseTimelineTooltip.propTypes = {
//   pipelineId: PropTypes.string.isRequired,
//   children: PropTypes.node.isRequired,
// };
