import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Typography, Card, Spin, Button, Progress, Tabs, 
  List, Tag, Empty, message, Divider, Space, Alert, Row, Col, Statistic,
  Modal, Form, Radio, Checkbox, Popover
} from 'antd';
import { 
  DownloadOutlined, FilePdfOutlined, FileTextOutlined,
  LeftOutlined, RobotOutlined, CheckCircleOutlined,
  FileOutlined, EyeOutlined,
  Html5Outlined, ExportOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { detectApi, reportApi } from '../api/api';
import { showSuccess, handleApiError, notifySuccess } from '../utils/notification';
import '../styles/Result.css';

const { Title, Paragraph, Text } = Typography;

const ResultPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [activeTabKey, setActiveTabKey] = useState('overview');
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [exportForm] = Form.useForm();
  const [templatePreviewVisible, setTemplatePreviewVisible] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState('standard');
  
  // 报告导出配置选项
  const exportFormats = [
    { value: 'pdf', label: 'PDF 格式', icon: <FilePdfOutlined /> },
    { value: 'html', label: 'HTML 格式', icon: <Html5Outlined /> },
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
      setResult(response);
      
      // 如果任务还在处理中
      if (response.status === 'processing') {
        // 轮询状态
        const intervalId = setInterval(async () => {
          try {
            const updatedResponse = await detectApi.getDetectionStatus(taskId);
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
    const { format, template, includeOptions } = values;
    
    setDownloading(true);
    
    try {
      let reportBlob;
      let filename = `ai_detection_report_${taskId}`;
      let fileExt = format;
      
      // 构建导出选项
      const exportOptions = {
        template,
        includeChart: includeOptions.includes('chart'),
        includeDetails: includeOptions.includes('details'),
        includeOriginalText: includeOptions.includes('originalText'),
        includeMetadata: includeOptions.includes('metadata'),
        includeHeaderFooter: includeOptions.includes('headerFooter')
      };
      
      // 根据格式选择导出方法
      if (format === 'pdf') {
        reportBlob = await reportApi.getPdfReport(taskId, exportOptions);
        fileExt = 'pdf';
      } else if (format === 'html') {
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
  
  // 快速下载PDF报告（不打开导出配置窗口）
  const handleQuickPdfDownload = async () => {
    try {
      setDownloading(true);
      const pdfBlob = await reportApi.getPdfReport(taskId);
      
      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([pdfBlob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `ai_detection_report_${taskId}.pdf`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      showSuccess('PDF报告下载成功');
    } catch (error) {
      handleApiError(error, '下载PDF报告失败');
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

  const getStatusTag = (status) => {
    switch (status) {
      case 'uploaded':
        return <Tag color="blue">待检测</Tag>;
      case 'processing':
        return <Tag color="orange">检测中</Tag>;
      case 'completed':
        return <Tag color="green">已完成</Tag>;
      case 'failed':
        return <Tag color="red">失败</Tag>;
      default:
        return <Tag>未知</Tag>;
    }
  };

  const renderPieChart = () => {
    if (!result || !result.ai_generated_percentage) return null;
    
    const option = {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}%'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        data: ['AI生成内容', '人类撰写内容']
      },
      series: [
        {
          name: '内容来源',
          type: 'pie',
          radius: ['50%', '70%'],
          avoidLabelOverlap: false,
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: '18',
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: false
          },
          data: [
            { value: result.ai_generated_percentage, name: 'AI生成内容', itemStyle: { color: '#ff4d4f' } },
            { value: 100 - result.ai_generated_percentage, name: '人类撰写内容', itemStyle: { color: '#52c41a' } }
          ]
        }
      ]
    };
    
    return <ReactECharts option={option} style={{ height: 400 }} />;
  };

  const getAIParagraphs = () => {
    if (!result || !result.details) return [];
    return result.details.filter(item => item.ai_generated);
  };

  const getHumanParagraphs = () => {
    if (!result || !result.details) return [];
    return result.details.filter(item => !item.ai_generated);
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
    <div className="result-page">
      <div style={{ marginBottom: 20 }}>
        <Button icon={<LeftOutlined />} onClick={() => navigate('/dashboard')}>
          返回首页
        </Button>
      </div>
      
      <Card className="result-card">
        <div className="result-summary">
          <Title level={2}>AI内容检测报告</Title>
          <div style={{ marginBottom: 20 }}>
            <Space split={<Divider type="vertical" />}>
              <Text>任务ID: {taskId}</Text>
              <Text>状态: {getStatusTag(result.status)}</Text>
              <Text>检测时间: {new Date(result.created_at).toLocaleString()}</Text>
            </Space>
          </div>
          
          <div style={{ marginBottom: 20 }}>
            <Progress
              type="circle"
              percent={result.ai_generated_percentage}
              format={percent => `${percent.toFixed(1)}%`}
              strokeColor={result.ai_generated_percentage > 50 ? '#ff4d4f' : '#1890ff'}
              width={120}
            />
            <div style={{ marginTop: 10 }}>
              <Text strong>AI生成内容比例</Text>
            </div>
            {result.ai_generated_percentage > 50 ? (
              <Alert
                message="高AI内容比例"
                description="检测到较高比例的AI生成内容，建议审查论文。"
                type="warning"
                showIcon
                style={{ maxWidth: 500, margin: '20px auto', textAlign: 'left' }}
              />
            ) : (
              <Alert
                message="低AI内容比例"
                description="检测到的AI生成内容比例较低。"
                type="success"
                showIcon
                style={{ maxWidth: 500, margin: '20px auto', textAlign: 'left' }}
              />
            )}
          </div>
          
          <div style={{ marginTop: 20 }}>
            <Space>
              <Button 
                type="primary" 
                icon={<DownloadOutlined />} 
                loading={downloading} 
                onClick={handleQuickPdfDownload}
              >
                下载PDF报告
              </Button>
              <Popover
                content={
                  <div>
                    <p>选择导出格式并自定义报告内容</p>
                  </div>
                }
                title="导出选项"
                trigger="hover"
              >
                <Button 
                  icon={<ExportOutlined />} 
                  onClick={handleShowExportOptions}
                >
                  更多导出选项
                </Button>
              </Popover>
            </Space>
          </div>
        </div>
      </Card>
      
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
            format: 'pdf',
            template: 'standard',
            includeOptions: ['chart', 'details', 'metadata', 'headerFooter']
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
          
          <Form.Item 
            name="includeOptions" 
            label="包含内容"
          >
            <Checkbox.Group>
              <Row>
                <Col span={12}>
                  <Checkbox value="chart">包含图表</Checkbox>
                </Col>
                <Col span={12}>
                  <Checkbox value="details">包含详细分析</Checkbox>
                </Col>
                <Col span={12}>
                  <Checkbox value="originalText">包含原文</Checkbox>
                </Col>
                <Col span={12}>
                  <Checkbox value="metadata">包含元数据</Checkbox>
                </Col>
                <Col span={12}>
                  <Checkbox value="headerFooter">包含页眉页脚</Checkbox>
                </Col>
              </Row>
            </Checkbox.Group>
          </Form.Item>
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
      
      <Card className="result-card">
        <Tabs activeKey={activeTabKey} onChange={setActiveTabKey} items={[
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
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="人类撰写段落数"
                      value={getHumanParagraphs().length}
                      prefix={<CheckCircleOutlined />}
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
                renderItem={item => (
                  <List.Item>
                    <Card 
                      className="paragraph-card paragraph-ai" 
                      style={{ width: '100%', borderColor: '#ff4d4f' }}
                    >
                      <Paragraph>{item.paragraph}</Paragraph>
                      <div style={{ marginTop: 10 }}>
                        <Tag color="red">AI生成</Tag>
                        <Text type="secondary">原因: {item.reason}</Text>
                      </div>
                    </Card>
                  </List.Item>
                )}
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
                renderItem={item => (
                  <List.Item>
                    <Card 
                      className="paragraph-card paragraph-human" 
                      style={{ width: '100%', borderColor: '#52c41a' }}
                    >
                      <Paragraph>{item.paragraph}</Paragraph>
                      <div style={{ marginTop: 10 }}>
                        <Tag color="green">人类撰写</Tag>
                        <Text type="secondary">原因: {item.reason}</Text>
                      </div>
                    </Card>
                  </List.Item>
                )}
                locale={{
                  emptyText: <Empty description="未检测到人类撰写内容" />
                }}
              />
            )
          }
        ]} />
      </Card>
    </div>
  );
};

export default ResultPage; 