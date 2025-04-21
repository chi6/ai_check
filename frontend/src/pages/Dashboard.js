import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Typography, Statistic, Button, Empty, List, Tag, Spin } from 'antd';
import { FileTextOutlined, UploadOutlined, HistoryOutlined, RobotOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { userApi } from '../api/api';

const { Title, Paragraph } = Typography;

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const tasksData = await userApi.getTasks();
      setTasks(tasksData);
    } catch (error) {
      console.error('获取任务列表失败:', error);
    } finally {
      setLoading(false);
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

  const getRecentTasks = () => {
    return tasks.slice(0, 5); // 最近5条任务
  };

  const getCompletedTasksCount = () => {
    return tasks.filter(task => task.status === 'completed').length;
  };

  const getAverageAIPercentage = () => {
    const completedTasks = tasks.filter(task => 
      task.status === 'completed' && task.ai_generated_percentage !== null
    );
    
    if (completedTasks.length === 0) return 0;
    
    const sum = completedTasks.reduce((acc, task) => acc + task.ai_generated_percentage, 0);
    return (sum / completedTasks.length).toFixed(1);
  };

  return (
    <div>
      <Title level={2}>欢迎使用AI论文检测工具</Title>
      <Paragraph>本工具可以帮助您检测论文中由AI生成的内容比例，提供详细的分析报告。</Paragraph>
      
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总检测任务"
              value={tasks.length}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="已完成检测"
              value={getCompletedTasksCount()}
              prefix={<HistoryOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="平均AI内容比例"
              value={getAverageAIPercentage()}
              suffix="%"
              prefix={<RobotOutlined />}
            />
          </Card>
        </Col>
      </Row>
      
      <div style={{ marginTop: 24, marginBottom: 12 }}>
        <Title level={3}>快速操作</Title>
      </div>
      
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12}>
          <Button 
            type="primary" 
            size="large" 
            icon={<UploadOutlined />}
            onClick={() => navigate('/upload')}
            style={{ width: '100%', height: 80 }}
          >
            上传新论文
          </Button>
        </Col>
        <Col xs={24} sm={12}>
          <Button 
            size="large" 
            icon={<HistoryOutlined />}
            onClick={() => navigate('/history')}
            style={{ width: '100%', height: 80 }}
          >
            查看历史检测记录
          </Button>
        </Col>
      </Row>
      
      <div style={{ marginTop: 24, marginBottom: 12 }}>
        <Title level={3}>最近检测记录</Title>
      </div>
      
      {loading ? (
        <div style={{ textAlign: 'center', padding: 20 }}>
          <Spin />
        </div>
      ) : getRecentTasks().length > 0 ? (
        <List
          bordered
          dataSource={getRecentTasks()}
          renderItem={item => (
            <List.Item
              actions={[
                <Link to={`/result/${item.id}`}>查看详情</Link>
              ]}
            >
              <List.Item.Meta
                title={<span>{item.filename}</span>}
                description={`检测时间: ${new Date(item.created_at).toLocaleString()}`}
              />
              <div>
                {getStatusTag(item.status)}
                {item.ai_generated_percentage !== null && (
                  <span style={{ marginLeft: 8 }}>
                    AI内容: {item.ai_generated_percentage.toFixed(1)}%
                  </span>
                )}
              </div>
            </List.Item>
          )}
        />
      ) : (
        <Empty description="暂无检测记录" />
      )}
    </div>
  );
};

export default Dashboard; 