import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Typography, Card, Spin, Button, Progress, Tabs, 
  List, Tag, Empty, message, Divider, Space, Alert, Row, Col, Statistic
} from 'antd';
import { 
  DownloadOutlined, FilePdfOutlined, FileTextOutlined,
  LeftOutlined, RobotOutlined, CheckCircleOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { detectApi, reportApi } from '../api/api';

const { Title, Paragraph, Text } = Typography;

const ResultPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [detailData, setDetailData] = useState(null);
  const [activeTabKey, setActiveTabKey] = useState('overview');

  useEffect(() => {
    if (taskId) {
      fetchDetectionResult();
    }
  }, [taskId]);

  const fetchDetectionResult = async () => {
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
  };

  const fetchDetailedReport = async () => {
    try {
      const reportData = await reportApi.getJsonReport(taskId);
      setDetailData(reportData);
    } catch (error) {
      console.error('获取详细报告失败:', error);
      message.error('获取详细报告失败');
    }
  };

  const handleDownloadPdf = async () => {
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
      
      message.success('PDF报告下载成功');
    } catch (error) {
      console.error('下载PDF报告失败:', error);
      message.error('下载PDF报告失败');
    } finally {
      setDownloading(false);
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
                <Button type="primary" onClick={() => detectApi.startDetection(taskId)}>开始检测</Button>
              </>
            )}
          </div>
        </Card>
      </div>
    );
  }

  // 任务已完成，显示结果
  return (
    <div>
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
            <Button 
              type="primary" 
              icon={<DownloadOutlined />} 
              loading={downloading} 
              onClick={handleDownloadPdf}
            >
              下载PDF报告
            </Button>
          </div>
        </div>
      </Card>
      
      <Card className="result-card">
        <Tabs activeKey={activeTabKey} onChange={setActiveTabKey}>
          <Tabs.TabPane 
            tab={
              <span>
                <FileTextOutlined />
                概览
              </span>
            } 
            key="overview"
          >
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
          </Tabs.TabPane>
          
          <Tabs.TabPane 
            tab={
              <span>
                <RobotOutlined />
                AI生成内容
              </span>
            } 
            key="ai"
          >
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
          </Tabs.TabPane>
          
          <Tabs.TabPane 
            tab={
              <span>
                <CheckCircleOutlined />
                人类撰写内容
              </span>
            } 
            key="human"
          >
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
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default ResultPage; 