import React, { useState, useEffect } from 'react';
import { Table, Typography, Tag, Button, Space, Empty, Spin, message, Tooltip, Input } from 'antd';
import { 
  SearchOutlined, EyeOutlined, DownloadOutlined, 
  FilterOutlined, RobotOutlined
} from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { userApi, reportApi } from '../api/api';

const { Title, Paragraph, Text } = Typography;
const { Search } = Input;

const History = () => {
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState([]);
  const [filteredTasks, setFilteredTasks] = useState([]);
  const [downloading, setDownloading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState(null);
  
  const navigate = useNavigate();

  useEffect(() => {
    fetchTasks();
  }, []);

  useEffect(() => {
    filterTasks();
  }, [tasks, searchText, statusFilter]);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const tasksData = await userApi.getTasks();
      
      // 按时间倒序排序
      const sortedTasks = tasksData.sort((a, b) => {
        return new Date(b.created_at) - new Date(a.created_at);
      });
      
      setTasks(sortedTasks);
      setFilteredTasks(sortedTasks);
    } catch (error) {
      console.error('获取任务列表失败:', error);
      message.error('获取历史记录失败，请稍后再试');
    } finally {
      setLoading(false);
    }
  };

  const filterTasks = () => {
    let result = [...tasks];
    
    // 按文件名搜索
    if (searchText) {
      result = result.filter(task => 
        task.filename.toLowerCase().includes(searchText.toLowerCase())
      );
    }
    
    // 按状态筛选
    if (statusFilter) {
      result = result.filter(task => task.status === statusFilter);
    }
    
    setFilteredTasks(result);
  };

  const handleDownloadPdf = async (taskId) => {
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

  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => getStatusTag(status),
      filters: [
        { text: '待检测', value: 'uploaded' },
        { text: '检测中', value: 'processing' },
        { text: '已完成', value: 'completed' },
        { text: '失败', value: 'failed' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: 'AI内容比例',
      dataIndex: 'ai_generated_percentage',
      key: 'ai_generated_percentage',
      render: (value) => {
        if (value === null) return '暂无数据';
        return (
          <Space>
            <RobotOutlined style={{ color: value > 50 ? '#ff4d4f' : '#1890ff' }} />
            <span>{value.toFixed(1)}%</span>
          </Space>
        );
      },
      sorter: (a, b) => {
        if (a.ai_generated_percentage === null) return 1;
        if (b.ai_generated_percentage === null) return -1;
        return a.ai_generated_percentage - b.ai_generated_percentage;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) => new Date(text).toLocaleString(),
      sorter: (a, b) => new Date(a.created_at) - new Date(b.created_at),
      defaultSortOrder: 'descend',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button 
              type="primary" 
              size="small" 
              icon={<EyeOutlined />} 
              onClick={() => navigate(`/result/${record.id}`)}
              disabled={record.status !== 'completed'}
            />
          </Tooltip>
          <Tooltip title="下载报告">
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownloadPdf(record.id)}
              disabled={record.status !== 'completed' || downloading}
              loading={downloading}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const handleSearch = (value) => {
    setSearchText(value);
  };

  const handleReset = () => {
    setSearchText('');
    setStatusFilter(null);
    setFilteredTasks(tasks);
  };

  const handleStatusChange = (status) => {
    setStatusFilter(status === statusFilter ? null : status);
  };

  return (
    <div>
      <Title level={2}>历史检测记录</Title>
      <Paragraph>查看您的所有历史检测任务及结果。</Paragraph>
      
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Search
            placeholder="搜索文件名"
            allowClear
            onSearch={handleSearch}
            style={{ width: 250 }}
          />
          <Space>
            <Button 
              type={statusFilter === 'uploaded' ? 'primary' : 'default'} 
              onClick={() => handleStatusChange('uploaded')}
            >
              待检测
            </Button>
            <Button 
              type={statusFilter === 'processing' ? 'primary' : 'default'} 
              onClick={() => handleStatusChange('processing')}
            >
              检测中
            </Button>
            <Button 
              type={statusFilter === 'completed' ? 'primary' : 'default'} 
              onClick={() => handleStatusChange('completed')}
            >
              已完成
            </Button>
            <Button 
              type={statusFilter === 'failed' ? 'primary' : 'default'} 
              onClick={() => handleStatusChange('failed')}
            >
              失败
            </Button>
          </Space>
          <Button onClick={handleReset}>重置筛选</Button>
        </Space>
      </div>
      
      {loading ? (
        <div style={{ textAlign: 'center', padding: 100 }}>
          <Spin size="large" />
        </div>
      ) : filteredTasks.length > 0 ? (
        <Table 
          columns={columns} 
          dataSource={filteredTasks.map(task => ({ ...task, key: task.id }))} 
          pagination={{ 
            pageSize: 10,
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      ) : (
        <Empty description={searchText || statusFilter ? "没有符合条件的记录" : "暂无检测记录"} />
      )}
      
      {!loading && tasks.length > 0 && filteredTasks.length === 0 && (
        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <Button onClick={handleReset}>重置筛选条件</Button>
        </div>
      )}
    </div>
  );
};

export default History; 