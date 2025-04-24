import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Typography, Card, Spin, Button, Progress, Tabs, 
  List, Tag, Empty, message, Divider, Space, Alert, Row, Col, Statistic,
  Modal, Form, Radio, Popover, Tooltip, Badge
} from 'antd';
import { 
  DownloadOutlined, FileTextOutlined,
  LeftOutlined, RobotOutlined, CheckCircleOutlined,
  FileOutlined, EyeOutlined, InfoCircleOutlined,
  Html5Outlined, ExportOutlined, QuestionCircleOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { detectApi, reportApi } from '../api/api';
import { showSuccess, handleApiError, notifySuccess } from '../utils/notification';
import '../styles/Result.css';

const { Title, Paragraph } = Typography;

const ResultPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [exportForm] = Form.useForm();
  const [templatePreviewVisible, setTemplatePreviewVisible] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState('standard');
  
  // 全局辅助函数，将其移至组件顶层，使其在整个组件内可用
  const getAILikelihoodColor = (likelihood) => {
    if (!likelihood) return '#999999';
    if (likelihood.includes('高')) return '#ff4d4f';
    if (likelihood.includes('中')) return '#faad14';
    return '#52c41a';
  };
  
  // 渲染段落数量警告，移至组件顶层
  const renderSegmentCountWarning = (count) => {
    if (!count || count > 2) return null;
    
    return (
      <Alert
        message="文本段落数量较少"
        description={
          <div>
            <p>当前分析基于 <strong>{count}</strong> 个文本段落，数量较少可能影响分析准确性。</p>
            <p>在段落少的情况下：</p>
            <ul>
              <li>风格一致性指标可能不准确</li>
              <li>AI内容比例可能会出现极端值（0%或100%）</li>
              <li>系统会更依赖单个段落的困惑度和LLM分析结果</li>
            </ul>
            <p>建议提供更多文本以获得更准确的分析结果。</p>
          </div>
        }
        type="warning"
        showIcon
        style={{ marginTop: 16, marginBottom: 16 }}
      />
    );
  };
  
  // 报告导出配置选项
  const exportFormats = [
    { value: 'html', label: 'HTML 格式', icon: <Html5Outlined style={{color: '#1890ff'}} /> },
    { value: 'text', label: '纯文本格式', icon: <FileOutlined /> }
  ];
  
  const reportTemplates = [
    { value: 'standard', label: '标准报告', description: '包含基本检测信息和结果摘要' },
    { value: 'detailed', label: '详细报告', description: '包含所有检测段落和详细分析' },
    { value: 'simple', label: '简洁报告', description: '仅包含关键检测结果和数据' }
  ];

  const fetchDetailedReport = useCallback(async () => {
    try {
      // eslint-disable-next-line no-unused-vars
      const reportData = await reportApi.getJsonReport(taskId);
    } catch (error) {
      console.error('获取详细报告失败:', error);
      message.error('获取详细报告失败');
    }
  }, [taskId]);

  const fetchDetectionResult = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 获取检测状态
      const response = await detectApi.getDetectionStatus(taskId);
      console.log('获取到的检测结果:', response);
      
      // 确保详细信息中的指标被正确处理
      if (response.details && response.details.length > 0) {
        // 检查段落详情中是否包含所有必要的指标字段
        response.details = response.details.map(detail => ({
          ...detail,
          perplexity: detail.perplexity !== undefined ? detail.perplexity : null,
          // 处理可能的格式不一致问题
          ai_likelihood: detail.ai_likelihood || null
        }));
      }
      
      // 确保整体分析结果中包含必要的字段
      if (response.overall_analysis) {
        // 后端可能使用perplexity或avg_perplexity字段
        const backendPerplexity = response.overall_analysis.perplexity !== undefined 
          ? response.overall_analysis.perplexity 
          : response.overall_analysis.avg_perplexity;
        
        // 优先使用顶级的ai_generated_percentage字段，如果不存在再使用overall_analysis中的ai_percentage
        const aiPercentage = response.ai_generated_percentage !== undefined && response.ai_generated_percentage !== null
          ? response.ai_generated_percentage
          : (response.overall_analysis.ai_percentage !== undefined ? response.overall_analysis.ai_percentage : 0);
        
        response.overall_analysis = {
          ...response.overall_analysis,
          avg_perplexity: backendPerplexity || 0,
          perplexity: backendPerplexity || 0,
          style_consistency: response.overall_analysis.style_consistency || 0,
          ai_likelihood: response.overall_analysis.ai_likelihood || '未知',
          ai_percentage: aiPercentage,  // 确保ai_percentage字段一定存在
          segment_count: response.overall_analysis.segment_count || 
            (response.details ? response.details.length : 0)
        };

        console.log('处理后的整体分析结果:', response.overall_analysis);
      } else if (response.ai_generated_percentage !== undefined && response.ai_generated_percentage !== null) {
        // 如果没有overall_analysis但有顶级ai_generated_percentage字段，创建一个最小的overall_analysis
        response.overall_analysis = {
          ai_percentage: response.ai_generated_percentage,
          perplexity: response.overall_perplexity || 0,
          style_consistency: 0,
          ai_likelihood: '未知',
          segment_count: response.details ? response.details.length : 0
        };
        
        console.log('创建的最小分析结果:', response.overall_analysis);
      }
      
      setResult(response);
      
      // 如果任务还在处理中
      if (response.status === 'processing') {
        // 轮询状态
        const intervalId = setInterval(async () => {
          try {
            const updatedResponse = await detectApi.getDetectionStatus(taskId);
            // 处理更新的响应，确保字段正确
            if (updatedResponse.details && updatedResponse.details.length > 0) {
              updatedResponse.details = updatedResponse.details.map(detail => ({
                ...detail,
                perplexity: detail.perplexity !== undefined ? detail.perplexity : null,
                ai_likelihood: detail.ai_likelihood || null
              }));
            }
            
            if (updatedResponse.overall_analysis) {
              // 后端可能使用perplexity或avg_perplexity字段
              const backendPerplexity = updatedResponse.overall_analysis.perplexity !== undefined 
                ? updatedResponse.overall_analysis.perplexity 
                : updatedResponse.overall_analysis.avg_perplexity;
              
              // 优先使用顶级的ai_generated_percentage字段
              const aiPercentage = updatedResponse.ai_generated_percentage !== undefined && updatedResponse.ai_generated_percentage !== null
                ? updatedResponse.ai_generated_percentage
                : (updatedResponse.overall_analysis.ai_percentage !== undefined ? updatedResponse.overall_analysis.ai_percentage : 0);
              
              updatedResponse.overall_analysis = {
                ...updatedResponse.overall_analysis,
                avg_perplexity: backendPerplexity || 0,
                perplexity: backendPerplexity || 0, 
                style_consistency: updatedResponse.overall_analysis.style_consistency || 0,
                ai_likelihood: updatedResponse.overall_analysis.ai_likelihood || '未知',
                ai_percentage: aiPercentage,  // 确保ai_percentage字段一定存在
                segment_count: updatedResponse.overall_analysis.segment_count || 
                  (updatedResponse.details ? updatedResponse.details.length : 0)
              };
            } else if (updatedResponse.ai_generated_percentage !== undefined && updatedResponse.ai_generated_percentage !== null) {
              // 如果没有overall_analysis但有顶级ai_generated_percentage字段
              updatedResponse.overall_analysis = {
                ai_percentage: updatedResponse.ai_generated_percentage,
                perplexity: updatedResponse.overall_perplexity || 0,
                style_consistency: 0,
                ai_likelihood: '未知',
                segment_count: updatedResponse.details ? updatedResponse.details.length : 0
              };
            }
            
            setResult(updatedResponse);
            
            if (updatedResponse.status !== 'processing') {
              clearInterval(intervalId);
            }
          } catch (error) {
            console.error('获取检测状态失败:', error);
            clearInterval(intervalId);
          }
        }, 5000);
        
        // 清理定时器
        return () => clearInterval(intervalId);
      }
      
      // 如果状态为已完成，获取详细报告
      if (response.status === 'completed') {
        fetchDetailedReport();
      }
    } catch (error) {
      console.error('获取结果失败:', error);
      setError('获取检测结果失败：' + (error.response?.data?.detail || '请稍后再试'));
    } finally {
      setLoading(false);
    }
  }, [taskId, fetchDetailedReport]);

  useEffect(() => {
    if (taskId) {
      fetchDetectionResult();
    }
  }, [taskId, fetchDetectionResult]);

  const exportReport = async (values) => {
    const { format, template } = values;
    
    setDownloading(true);
    
    try {
      let reportBlob;
      let filename = `ai_detection_report_${taskId}`;
      let fileExt = format;
      
      // 根据模板自动设置导出选项
      const exportOptions = {
        template,
        includeChart: template !== 'simple',
        includeDetails: template === 'detailed',
        includeOriginalText: template === 'detailed',
        includeMetadata: template !== 'simple',
        includeHeaderFooter: true
      };
      
      // 根据格式选择导出方法
      if (format === 'html') {
        reportBlob = await reportApi.getHtmlReport(taskId, exportOptions);
        fileExt = 'html';
      } else if (format === 'text') {
        reportBlob = await reportApi.getTextReport(taskId, exportOptions);
        fileExt = 'txt';
      }
      
      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([reportBlob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${filename}.${fileExt}`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      notifySuccess('报告导出成功', `${format.toUpperCase()}报告已成功下载`);
      setExportModalVisible(false);
    } catch (error) {
      handleApiError(error, `导出${format.toUpperCase()}报告失败`);
    } finally {
      setDownloading(false);
    }
  };
  
  // 快速下载HTML报告（不打开导出配置窗口）
  const handleQuickHtmlDownload = async () => {
    try {
      setDownloading(true);
      
      // 使用标准模板的导出选项
      const exportOptions = {
        template: 'standard',
        includeChart: true,
        includeDetails: false,
        includeOriginalText: false,
        includeMetadata: true,
        includeHeaderFooter: true
      };
      
      const htmlBlob = await reportApi.getHtmlReport(taskId, exportOptions);
      
      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([htmlBlob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `ai_detection_report_${taskId}.html`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      showSuccess('HTML报告下载成功');
    } catch (error) {
      handleApiError(error, '下载HTML报告失败');
    } finally {
      setDownloading(false);
    }
  };
  
  // 显示导出选项窗口
  const handleShowExportOptions = () => {
    exportForm.resetFields();
    setExportModalVisible(true);
  };
  
  // 切换模板预览
  const handleTemplateChange = (e) => {
    setSelectedTemplate(e.target.value);
  };
  
  // 预览模板
  const handlePreviewTemplate = () => {
    setTemplatePreviewVisible(true);
  };
  
  // 渲染模板预览内容
  const renderTemplatePreview = () => {
    switch (selectedTemplate) {
      case 'standard':
        return (
          <div className="template-preview standard-template">
            <div className="preview-header">
              <h3>标准报告预览</h3>
            </div>
            <div className="preview-content">
              <div className="preview-section">
                <h4>报告概述</h4>
                <div className="preview-line"></div>
                <div className="preview-line short"></div>
              </div>
              <div className="preview-section">
                <h4>检测结果</h4>
                <div className="preview-chart"></div>
                <div className="preview-line"></div>
                <div className="preview-line short"></div>
              </div>
              <div className="preview-section">
                <h4>AI内容摘要</h4>
                <div className="preview-block"></div>
                <div className="preview-block"></div>
              </div>
            </div>
          </div>
        );
      case 'detailed':
        return (
          <div className="template-preview detailed-template">
            <div className="preview-header">
              <h3>详细报告预览</h3>
            </div>
            <div className="preview-content">
              <div className="preview-section">
                <h4>报告概述</h4>
                <div className="preview-line"></div>
                <div className="preview-line short"></div>
              </div>
              <div className="preview-section">
                <h4>检测结果</h4>
                <div className="preview-chart"></div>
                <div className="preview-line"></div>
                <div className="preview-line"></div>
              </div>
              <div className="preview-section">
                <h4>段落详细分析</h4>
                <div className="preview-paragraph">
                  <div className="preview-paragraph-header ai"></div>
                  <div className="preview-paragraph-content"></div>
                </div>
                <div className="preview-paragraph">
                  <div className="preview-paragraph-header human"></div>
                  <div className="preview-paragraph-content"></div>
                </div>
                <div className="preview-paragraph">
                  <div className="preview-paragraph-header ai"></div>
                  <div className="preview-paragraph-content"></div>
                </div>
              </div>
              <div className="preview-section">
                <h4>分析方法说明</h4>
                <div className="preview-line"></div>
                <div className="preview-line"></div>
              </div>
            </div>
          </div>
        );
      case 'simple':
        return (
          <div className="template-preview simple-template">
            <div className="preview-header">
              <h3>简洁报告预览</h3>
            </div>
            <div className="preview-content">
              <div className="preview-section">
                <h4>检测结果摘要</h4>
                <div className="preview-line"></div>
                <div className="preview-chart simple"></div>
              </div>
              <div className="preview-section">
                <h4>关键数据</h4>
                <div className="preview-stats"></div>
              </div>
            </div>
          </div>
        );
      default:
        return <div>无预览</div>;
    }
  };

  const renderPieChart = () => {
    if (!result || !result.details || result.details.length === 0) {
      return <Empty description="暂无数据" />;
    }
    
    const aiCount = getAIParagraphs().length;
    const humanCount = getHumanParagraphs().length;
    
    // 计算实际的AI百分比，确保与整体显示一致
    let aiPercentage = 0;
    if (result.overall_analysis && result.overall_analysis.ai_percentage !== undefined) {
      // 优先使用整体分析中的百分比
      aiPercentage = result.overall_analysis.ai_percentage;
    } else if (aiCount + humanCount > 0) {
      // 根据段落计算百分比
      aiPercentage = (aiCount / (aiCount + humanCount)) * 100;
    }
    
    const humanPercentage = 100 - aiPercentage;
    
    const option = {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'horizontal',
        bottom: 'bottom',
        data: ['AI生成内容', '人类撰写内容']
      },
      series: [
        {
          type: 'pie',
          radius: '70%',
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          label: {
            show: true,
            formatter: '{b}: {d}%',
            position: 'outside'
          },
          data: [
            {
              value: aiPercentage,
              name: 'AI生成内容',
              itemStyle: { color: '#ff4d4f' }
            },
            {
              value: humanPercentage,
              name: '人类撰写内容',
              itemStyle: { color: '#52c41a' }
            }
          ],
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    };
    
    return (
      <ReactECharts
        option={option}
        style={{ height: 300, width: '100%' }}
        opts={{ renderer: 'canvas' }}
      />
    );
  };

  const renderAdvancedMetrics = () => {
    if (!result || !result.overall_analysis) {
      return <Empty description="暂无高级分析数据" />;
    }
    
    const {
      avg_perplexity, 
      style_consistency, 
      ai_likelihood,
      segment_count,
      perplexity
    } = result.overall_analysis;
    
    // 使用通用格式化函数处理AI可能性
    const { mainLevel, description } = formatAILikelihood(ai_likelihood);
    
    // 使用perplexity字段，如果不存在则尝试avg_perplexity或默认为0
    const actualPerplexity = perplexity !== undefined ? perplexity : 
                            (avg_perplexity !== undefined ? avg_perplexity : 0);
    
    const renderPerplexityPopover = () => (
      <div style={{ maxWidth: 280 }}>
        <Typography.Title level={5}>什么是困惑度？</Typography.Title>
        <Typography.Paragraph>
          困惑度(Perplexity)是衡量语言模型预测文本难度的指标。AI生成的文本通常具有较低的困惑度（&lt;20），因为AI更倾向于使用高概率的词组合。
        </Typography.Paragraph>
        <Typography.Paragraph>
          <ul>
            <li><b>&lt;20</b>: 高度可能是AI生成</li>
            <li><b>20-30</b>: 中等可能是AI生成</li>
            <li><b>&gt;30</b>: 较低可能是AI生成</li>
          </ul>
        </Typography.Paragraph>
      </div>
    );
    
    const renderStyleConsistencyPopover = () => (
      <div style={{ maxWidth: 280 }}>
        <Typography.Title level={5}>什么是风格一致性？</Typography.Title>
        <Typography.Paragraph>
          风格一致性衡量文本各部分在风格和表达方式上的相似程度。AI生成的文本往往具有高度一致的风格特征，而人类写作的风格可能更为多变。
        </Typography.Paragraph>
        <Typography.Paragraph>
          <ul>
            <li><b>&gt;0.9</b>: 高度一致，常见于AI生成</li>
            <li><b>0.8-0.9</b>: 中等一致性</li>
            <li><b>&lt;0.8</b>: 低一致性，常见于人类写作</li>
          </ul>
        </Typography.Paragraph>
      </div>
    );
    
    return (
      <div className="advanced-metrics-container">
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8} md={8}>
            <Card bordered={false} className="metric-card">
              <Statistic
                title={
                  <span>
                    平均困惑度
                    <Popover content={renderPerplexityPopover()} title="困惑度说明">
                      <QuestionCircleOutlined style={{ marginLeft: 8 }} />
                    </Popover>
                  </span>
                }
                value={actualPerplexity || 0}
                precision={2}
                suffix={actualPerplexity < 20 ? 
                  <Tooltip title="较低的困惑度通常表示AI生成的可能性较高">
                    <Badge status="error" text="低" />
                  </Tooltip> : 
                  (actualPerplexity < 30 ? 
                    <Badge status="warning" text="中" /> : 
                    <Badge status="success" text="高" />
                  )
                }
              />
            </Card>
          </Col>
          
          <Col xs={24} sm={8} md={8}>
            <Card bordered={false} className="metric-card">
              <Statistic
                title={
                  <span>
                    风格一致性
                    <Popover content={renderStyleConsistencyPopover()} title="风格一致性说明">
                      <QuestionCircleOutlined style={{ marginLeft: 8 }} />
                    </Popover>
                  </span>
                }
                value={style_consistency !== undefined ? style_consistency : 0}
                precision={3}
                suffix={style_consistency > 0.9 ? 
                  <Tooltip title="高度一致的风格可能表示AI生成">
                    <Badge status="error" text="高" />
                  </Tooltip> : 
                  (style_consistency > 0.8 ? 
                    <Badge status="warning" text="中" /> : 
                    <Badge status="success" text="低" />
                  )
                }
              />
            </Card>
          </Col>
          
          <Col xs={24} sm={8} md={8}>
            <Card bordered={false} className="metric-card">
              <Statistic
                title="AI生成可能性"
                value={mainLevel || "未知"}
                valueStyle={{ color: getAILikelihoodColor(ai_likelihood) }}
                suffix={
                  description ? (
                    <Tooltip title={description}>
                      <InfoCircleOutlined style={{ marginLeft: 4 }} />
                    </Tooltip>
                  ) : null
                }
              />
            </Card>
          </Col>
        </Row>
        
        {/* 将段落数量单独放在一行 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card bordered={false} className="metric-card">
              <Statistic
                title="分析段落数量"
                value={segment_count !== undefined ? segment_count : 0}
                suffix={
                  <Tooltip title={segment_count <= 2 ? "段落数量较少，分析结果可能受限" : "段落数量充足，分析结果更可靠"}>
                    <InfoCircleOutlined style={{ color: segment_count <= 2 ? '#faad14' : '#52c41a' }} />
                  </Tooltip>
                }
              />
              {renderSegmentCountWarning(segment_count)}
            </Card>
          </Col>
        </Row>
        
        <Divider orientation="left">指标解读</Divider>
        <Alert
          message="检测指标说明"
          description={
            <div>
              <p><strong>困惑度</strong>：衡量文本的可预测性，AI生成的文本通常困惑度较低（&lt;20）。</p>
              <p><strong>风格一致性</strong>：衡量文本各部分风格的一致程度，AI生成文本通常风格高度一致（&gt;0.9）。</p>
              <p><strong>段落数量</strong>：参与分析的文本段落数量，数量太少可能影响分析精度。</p>
              <p><strong>AI生成可能性</strong>：综合考虑困惑度、风格一致性、AI段落比例等因素的总体评估。</p>
            </div>
          }
          type="info"
          showIcon
        />
      </div>
    );
  };

  const getAIParagraphs = () => {
    if (!result || !result.details) return [];
    return result.details.filter(item => item.ai_generated);
  };

  const getHumanParagraphs = () => {
    if (!result || !result.details) return [];
    return result.details.filter(item => !item.ai_generated);
  };

  // 加强通用函数处理ai_likelihood格式的健壮性
  const formatAILikelihood = (value) => {
    if (!value) return { mainLevel: '未知', description: '' };
    
    // 处理各种可能的格式
    let mainLevel = value;
    let description = '';
    
    try {
      // 处理中文括号格式
      if (typeof value === 'string' && value.includes('（')) {
        const parts = value.split('（');
        mainLevel = parts[0];
        description = parts[1]?.replace('）', '') || '';
      } 
      // 处理英文括号格式
      else if (typeof value === 'string' && value.includes('(')) {
        const parts = value.split('(');
        mainLevel = parts[0];
        description = parts[1]?.replace(')', '') || '';
      }
      // 还可能有冒号分隔的格式
      else if (typeof value === 'string' && value.includes('：')) {
        const parts = value.split('：');
        mainLevel = parts[0];
        description = parts.slice(1).join('：');
      }
      
      // 统一去除空格
      mainLevel = String(mainLevel).trim();
      description = String(description).trim();
    } catch (e) {
      console.error('处理AI可能性格式时出错:', e);
      // 出错时返回安全值
      return { mainLevel: String(value).trim() || '未知', description: '' };
    }
    
    return { mainLevel, description };
  };

  // 渲染段落详情
  const renderParagraph = (item) => {
    const getPerplexityTag = (value) => {
      if (!value && value !== 0) return null;
      if (value < 20) return <Tag color="red">困惑度低: {value.toFixed(2)}</Tag>;
      if (value < 30) return <Tag color="orange">困惑度中: {value.toFixed(2)}</Tag>;
      return <Tag color="green">困惑度高: {value.toFixed(2)}</Tag>;
    };
    
    const getLikelihoodTag = (value) => {
      if (!value) return null;
      
      const { mainLevel } = formatAILikelihood(value);
      
      if (value.includes('高')) return <Tag color="red">AI可能性: {mainLevel}</Tag>;
      if (value.includes('中')) return <Tag color="orange">AI可能性: {mainLevel}</Tag>;
      return <Tag color="green">AI可能性: {mainLevel}</Tag>;
    };
    
    return (
      <List.Item key={item.paragraph.substring(0, 20)}>
        <Card 
          className={`paragraph-card ${item.ai_generated ? 'ai-generated' : 'human-written'}`}
          title={
            <div className="paragraph-header">
              <Badge 
                status={item.ai_generated ? 'error' : 'success'} 
                text={
                  <Typography.Text strong>
                    {item.ai_generated ? 'AI生成内容' : '人类撰写内容'}
                  </Typography.Text>
                } 
              />
            </div>
          }
          extra={
            <Space>
              {getPerplexityTag(item.perplexity)}
              {getLikelihoodTag(item.ai_likelihood)}
            </Space>
          }
        >
          <div className="paragraph-content">
            <Paragraph ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}>
              {item.paragraph}
            </Paragraph>
          </div>
          
          <Divider style={{ margin: '12px 0' }} />
          
          <div className="paragraph-reason">
            <Typography.Text type="secondary" strong>分析原因：</Typography.Text>
            <Typography.Paragraph style={{ margin: '8px 0 0' }}>
              {item.reason || '无分析原因'}
            </Typography.Paragraph>
          </div>
        </Card>
      </List.Item>
    );
  };

  const renderOverallResult = () => {
    if (!result || !result.overall_analysis) return null;
    
    const {
      ai_percentage,
      ai_likelihood,
      segment_count
    } = result.overall_analysis;
    
    // 获取实际显示的AI百分比，确保有值
    const displayAIPercentage = (ai_percentage !== undefined && ai_percentage !== null)
      ? ai_percentage
      : (result.ai_generated_percentage !== undefined && result.ai_generated_percentage !== null)
        ? result.ai_generated_percentage
        : 0;
    
    const { mainLevel, description } = formatAILikelihood(ai_likelihood);
    
    return (
      <div className="overall-result">
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <RobotOutlined style={{ marginRight: 8 }} />
              <span>整体评估结果</span>
              {segment_count && segment_count <= 2 && (
                <Tag color="warning" style={{ marginLeft: 12 }}>段落数量较少</Tag>
              )}
            </div>
          }
          bordered={false}
          className="result-summary-card"
        >
          <Row gutter={[16, 16]} align="middle">
            <Col xs={24} sm={12} md={8}>
              <Progress
                type="circle"
                percent={Math.round(displayAIPercentage || 0)}
                format={(percent) => `${percent}%`}
                strokeColor={
                  displayAIPercentage > 75 ? '#ff4d4f' : 
                  displayAIPercentage > 50 ? '#faad14' : 
                  displayAIPercentage > 25 ? '#52c41a' : 
                  '#52c41a'
                }
              />
            </Col>
            <Col xs={24} sm={12} md={16}>
              <div>
                <Typography.Title level={4}>
                  AI生成内容占比: {displayAIPercentage !== undefined ? displayAIPercentage.toFixed(1) : 0}%
                </Typography.Title>
                <Typography.Paragraph>
                  <strong>总体判断:</strong> 
                  <Tag 
                    color={getAILikelihoodColor(ai_likelihood)} 
                    style={{ marginLeft: 8, fontSize: '14px', padding: '4px 8px' }}
                  >
                    {mainLevel || '未知'}
                  </Tag>
                </Typography.Paragraph>
                {description && (
                  <Typography.Paragraph type="secondary">
                    {description}
                  </Typography.Paragraph>
                )}
              </div>
            </Col>
          </Row>
          
          {renderSegmentCountWarning(segment_count)}
        </Card>
      </div>
    );
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
        <Paragraph style={{ marginTop: 20 }}>正在加载检测结果...</Paragraph>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
        />
        <div style={{ marginTop: 20, textAlign: 'center' }}>
          <Button onClick={fetchDetectionResult}>重试</Button>
          <Button onClick={() => navigate('/dashboard')} style={{ marginLeft: 10 }}>
            返回首页
          </Button>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <Empty description="未找到检测结果" />
    );
  }

  // 如果任务未完成
  if (result.status !== 'completed') {
    return (
      <div>
        <Card>
          <div style={{ textAlign: 'center', padding: 30 }}>
            {result.status === 'processing' ? (
              <>
                <Spin />
                <Title level={3} style={{ marginTop: 20 }}>检测中...</Title>
                <Paragraph>正在进行AI内容检测，请稍候...</Paragraph>
                <Progress percent={50} status="active" style={{ maxWidth: 400, margin: '20px auto' }} />
              </>
            ) : result.status === 'failed' ? (
              <>
                <FileTextOutlined style={{ fontSize: 64, color: '#ff4d4f' }} />
                <Title level={3} style={{ marginTop: 20 }}>检测失败</Title>
                <Paragraph>很抱歉，检测过程发生错误。</Paragraph>
                <Button onClick={() => navigate('/upload')}>重新上传检测</Button>
              </>
            ) : (
              <>
                <FileTextOutlined style={{ fontSize: 64, color: '#1890ff' }} />
                <Title level={3} style={{ marginTop: 20 }}>等待检测</Title>
                <Paragraph>任务已上传，但尚未开始检测。</Paragraph>
                <Button type="primary" onClick={() => {
                  if (taskId && typeof taskId === 'string') {
                    console.log('Starting detection for task ID:', taskId);
                    detectApi.startDetection(taskId);
                  } else {
                    console.error('Invalid task ID:', taskId);
                    message.error('无效的任务ID，请返回上传页面重新上传');
                  }
                }}>开始检测</Button>
              </>
            )}
          </div>
        </Card>
      </div>
    );
  }

  // 任务已完成，显示结果
  return (
    <div className="result-container">
      <div className="result-header">
        <Button 
          icon={<LeftOutlined />}
          onClick={() => navigate('/dashboard')}
          style={{ marginBottom: 16 }}
        >
          返回
        </Button>
        
        <Card className="result-card">
          <Space direction="vertical" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography.Title level={4} style={{ margin: 0 }}>
                <FileTextOutlined /> {result?.filename || '文档分析'}
              </Typography.Title>
              
              <Space>
                <Button 
                  type="primary" 
                  icon={<DownloadOutlined />} 
                  onClick={handleQuickHtmlDownload}
                  loading={downloading}
                >
                  下载报告
                </Button>
                <Button 
                  icon={<ExportOutlined />}
                  onClick={handleShowExportOptions}
                >
                  导出选项
                </Button>
              </Space>
            </div>
            
            {renderOverallResult()}
            
            <Tabs defaultActiveKey="overview" items={[
              {
                key: 'overview',
                label: (
                  <span>
                    <FileTextOutlined />
                    概览
                  </span>
                ),
                children: (
                  <>
                    {renderAdvancedMetrics()}
                    
                    <Divider />
                    
                    <div style={{ textAlign: 'center', marginBottom: 20 }}>
                      <Title level={4}>内容分布</Title>
                      {renderPieChart()}
                    </div>
                    
                    <Row>
                      <Col span={12}>
                        <Statistic
                          title="AI生成段落数"
                          value={getAIParagraphs().length}
                          prefix={<RobotOutlined />}
                          suffix={
                            <span style={{ fontSize: '14px', marginLeft: '8px' }}>
                              {result.overall_analysis && result.overall_analysis.ai_percentage !== undefined ? 
                                `(${result.overall_analysis.ai_percentage.toFixed(1)}%)` : ''}
                            </span>
                          }
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="人类撰写段落数"
                          value={getHumanParagraphs().length}
                          prefix={<CheckCircleOutlined />}
                          suffix={
                            <span style={{ fontSize: '14px', marginLeft: '8px' }}>
                              {result.overall_analysis && result.overall_analysis.ai_percentage !== undefined ? 
                                `(${(100 - result.overall_analysis.ai_percentage).toFixed(1)}%)` : ''}
                            </span>
                          }
                        />
                      </Col>
                    </Row>
                  </>
                )
              },
              {
                key: 'ai',
                label: (
                  <span>
                    <RobotOutlined />
                    AI生成内容
                  </span>
                ),
                children: (
                  <List
                    dataSource={getAIParagraphs()}
                    renderItem={renderParagraph}
                    locale={{
                      emptyText: <Empty description="未检测到AI生成内容" />
                    }}
                  />
                )
              },
              {
                key: 'human',
                label: (
                  <span>
                    <CheckCircleOutlined />
                    人类撰写内容
                  </span>
                ),
                children: (
                  <List
                    dataSource={getHumanParagraphs()}
                    renderItem={renderParagraph}
                    locale={{
                      emptyText: <Empty description="未检测到人类撰写内容" />
                    }}
                  />
                )
              },
              {
                key: 'all',
                label: (
                  <span>
                    <FileOutlined />
                    完整分析
                  </span>
                ),
                children: (
                  <div className="all-paragraphs">
                    <Alert
                      message="段落分析说明"
                      description={
                        <ul>
                          <li>每个段落都经过独立分析，显示其AI生成可能性</li>
                          <li>困惑度 - 值越低，越可能是AI生成（通常小于20）</li>
                          <li>AI可能性 - 基于多个指标的综合评估</li>
                        </ul>
                      }
                      type="info"
                      showIcon
                      style={{ marginBottom: 20 }}
                    />
                    <List
                      dataSource={result.details || []}
                      renderItem={renderParagraph}
                      locale={{
                        emptyText: <Empty description="暂无分析结果" />
                      }}
                    />
                  </div>
                )
              },
              {
                key: 'method',
                label: (
                  <span>
                    <InfoCircleOutlined />
                    检测方法
                  </span>
                ),
                children: (
                  <div className="detection-method">
                    <Title level={4}>AI内容检测原理</Title>
                    <Paragraph>
                      本检测服务使用综合方法来检测文本中的AI生成内容，采用多种指标和模型：
                    </Paragraph>
                    
                    <Title level={5}>1. 困惑度分析</Title>
                    <Paragraph>
                      困惑度(Perplexity)是衡量语言模型预测文本难度的指标。AI生成的文本通常具有较低的困惑度，
                      因为语言模型生成的文本往往更加可预测。人类撰写的文本则更加多变和不可预测，困惑度较高。
                    </Paragraph>
                    
                    <Title level={5}>2. 风格一致性分析</Title>
                    <Paragraph>
                      对文本各部分的风格一致性进行评估。AI生成的文本风格通常非常一致，
                      而人类撰写的文本则风格略有变化。风格一致性过高可能表明是AI生成的内容。
                    </Paragraph>
                    
                    <Title level={5}>3. 语义内容审查</Title>
                    <Paragraph>
                      使用大型语言模型对文本内容进行分析，识别常见的AI生成特征，
                      如模板化表达、缺乏个人见解或创造性思考等。
                    </Paragraph>
                    
                    <Alert
                      message="注意"
                      description="检测结果供参考，不应作为唯一判断依据。技术在不断发展，检测方法也在持续改进。"
                      type="warning"
                      showIcon
                      style={{ marginTop: 20 }}
                    />
                  </div>
                )
              }
            ]} />
          </Space>
        </Card>
      </div>
      
      {/* 导出选项对话框 */}
      <Modal
        title="导出报告"
        open={exportModalVisible}
        onOk={() => exportForm.submit()}
        onCancel={() => setExportModalVisible(false)}
        confirmLoading={downloading}
        width={600}
      >
        <Form
          form={exportForm}
          layout="vertical"
          initialValues={{
            format: 'html',
            template: 'standard'
          }}
          onFinish={exportReport}
        >
          <Form.Item 
            name="format" 
            label="导出格式"
            rules={[{ required: true, message: '请选择导出格式' }]}
          >
            <Radio.Group>
              {exportFormats.map(format => (
                <Radio.Button value={format.value} key={format.value}>
                  {format.icon} {format.label}
                </Radio.Button>
              ))}
            </Radio.Group>
          </Form.Item>
          
          <Form.Item 
            name="template" 
            label={
              <Space>
                报告模板
                <Button type="link" size="small" onClick={handlePreviewTemplate} icon={<EyeOutlined />}>
                  预览
                </Button>
              </Space>
            }
            rules={[{ required: true, message: '请选择报告模板' }]}
          >
            <Radio.Group onChange={handleTemplateChange}>
              {reportTemplates.map(template => (
                <Radio value={template.value} key={template.value}>
                  <div>
                    <div>{template.label}</div>
                    <div className="template-description">{template.description}</div>
                  </div>
                </Radio>
              ))}
            </Radio.Group>
          </Form.Item>
          
          <div className="report-content-info">
            <div style={{ marginBottom: "10px" }}>
              <strong>报告将包含：</strong>
            </div>
            <Row>
              <Col span={12}>
                <div>✓ 检测结果概览</div>
              </Col>
              <Col span={12}>
                <div>✓ AI检测比例</div>
              </Col>
              {selectedTemplate !== 'simple' && (
                <>
                  <Col span={12}>
                    <div>✓ 图表展示</div>
                  </Col>
                  <Col span={12}>
                    <div>✓ 元数据信息</div>
                  </Col>
                </>
              )}
              {selectedTemplate === 'detailed' && (
                <>
                  <Col span={12}>
                    <div>✓ 详细段落分析</div>
                  </Col>
                  <Col span={12}>
                    <div>✓ 完整原始文本</div>
                  </Col>
                </>
              )}
            </Row>
            <div style={{ marginTop: "10px", color: "#888", fontSize: "12px" }}>
              * 注：不同模板包含的内容不同，详细模板包含最全面的信息
            </div>
          </div>
        </Form>
      </Modal>
      
      {/* 模板预览弹窗 */}
      <Modal
        title="报告模板预览"
        open={templatePreviewVisible}
        onCancel={() => setTemplatePreviewVisible(false)}
        footer={[
          <Button key="back" onClick={() => setTemplatePreviewVisible(false)}>
            关闭
          </Button>
        ]}
        width={600}
      >
        {renderTemplatePreview()}
      </Modal>
    </div>
  );
};

export default ResultPage; 