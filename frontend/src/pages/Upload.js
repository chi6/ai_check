import React, { useState } from 'react';
import { Upload, Button, Typography, Card, message, Steps, Progress, Space, Alert } from 'antd';
import { InboxOutlined, FileTextOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { uploadApi, detectApi } from '../api/api';

const { Dragger } = Upload;
const { Title, Paragraph, Text } = Typography;
const { Step } = Steps;

const UploadPage = () => {
  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadedTaskId, setUploadedTaskId] = useState(null);
  const [detecting, setDetecting] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  
  const navigate = useNavigate();

  const uploadProps = {
    name: 'file',
    multiple: false,
    fileList,
    beforeUpload: (file) => {
      // 检查文件类型
      const isValidType = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'].includes(file.type);
      if (!isValidType) {
        message.error('只支持PDF、DOCX和TXT格式的文件！');
        return Upload.LIST_IGNORE;
      }
      
      // 检查文件大小 (50MB)
      const isValidSize = file.size / 1024 / 1024 < 50;
      if (!isValidSize) {
        message.error('文件大小不能超过50MB！');
        return Upload.LIST_IGNORE;
      }
      
      // 设置文件列表
      setFileList([file]);
      return false; // 阻止自动上传
    },
    onRemove: () => {
      setFileList([]);
      setError(null);
    },
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择要上传的文件！');
      return;
    }
    
    setUploading(true);
    setError(null);
    setCurrentStep(0);
    
    try {
      // 上传文件
      const file = fileList[0];
      
      // 模拟进度
      let progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 300);
      
      const result = await uploadApi.uploadFile(file);
      
      clearInterval(progressInterval);
      setProgress(100);
      setCurrentStep(1);
      setUploadedTaskId(result.task_id);
      
      message.success('文件上传成功！');
    } catch (error) {
      console.error('上传失败:', error);
      setError('文件上传失败：' + (error.response?.data?.detail || '请稍后再试'));
    } finally {
      setUploading(false);
    }
  };

  const handleStartDetection = async () => {
    if (!uploadedTaskId) return;
    
    setDetecting(true);
    setError(null);
    
    try {
      // 开始检测
      await detectApi.startDetection(uploadedTaskId);
      
      // 检测进度轮询
      setProgress(0);
      let progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            return 90;
          }
          return prev + 5;
        });
      }, 1000);
      
      // 轮询检测状态
      let statusCheckInterval = setInterval(async () => {
        try {
          const result = await detectApi.getDetectionStatus(uploadedTaskId);
          if (result.status === 'completed') {
            clearInterval(statusCheckInterval);
            clearInterval(progressInterval);
            setProgress(100);
            setCurrentStep(2);
            message.success('检测完成！');
            // 导航到结果页面
            setTimeout(() => {
              navigate(`/result/${uploadedTaskId}`);
            }, 1000);
          } else if (result.status === 'failed') {
            clearInterval(statusCheckInterval);
            clearInterval(progressInterval);
            setError('检测失败，请重试！');
          }
        } catch (error) {
          console.error('获取检测状态失败:', error);
          clearInterval(statusCheckInterval);
          clearInterval(progressInterval);
          setError('获取检测状态失败，请刷新页面重试');
        }
      }, 3000);
      
    } catch (error) {
      console.error('开始检测失败:', error);
      setError('开始检测失败：' + (error.response?.data?.detail || '请稍后再试'));
    } finally {
      setDetecting(false);
    }
  };
  
  const handleViewResult = () => {
    navigate(`/result/${uploadedTaskId}`);
  };

  const steps = [
    {
      title: '上传论文',
      description: '上传PDF、DOCX或TXT格式的论文',
      icon: <InboxOutlined />
    },
    {
      title: '开始检测',
      description: '开始AI内容检测',
      icon: <FileTextOutlined />
    },
    {
      title: '查看结果',
      description: '查看检测报告',
      icon: <CheckCircleOutlined />
    }
  ];

  return (
    <div>
      <Title level={2}>上传论文检测</Title>
      <Paragraph>支持PDF、DOCX和TXT格式文件，文件大小不超过50MB。</Paragraph>
      
      <Steps current={currentStep} style={{ marginBottom: 30 }}>
        {steps.map(item => (
          <Step 
            key={item.title} 
            title={item.title} 
            description={item.description} 
            icon={item.icon} 
          />
        ))}
      </Steps>
      
      {error && (
        <Alert 
          message="错误" 
          description={error} 
          type="error" 
          showIcon 
          closable
          style={{ marginBottom: 20 }}
          icon={<CloseCircleOutlined />}
        />
      )}
      
      {currentStep === 0 && (
        <Card>
          <Dragger {...uploadProps} disabled={uploading}>
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">支持单个文件上传，仅支持PDF、DOCX和TXT格式</p>
          </Dragger>
          
          <div style={{ marginTop: 20, textAlign: 'center' }}>
            <Button 
              type="primary" 
              onClick={handleUpload} 
              loading={uploading} 
              disabled={fileList.length === 0}
              size="large"
            >
              {uploading ? '上传中...' : '开始上传'}
            </Button>
          </div>
          
          {uploading && (
            <div style={{ marginTop: 20 }}>
              <Text>上传进度：</Text>
              <Progress percent={progress} status="active" />
            </div>
          )}
        </Card>
      )}
      
      {currentStep === 1 && (
        <Card>
          <div style={{ textAlign: 'center' }}>
            <FileTextOutlined style={{ fontSize: 64, color: '#1890ff' }} />
            <Title level={4} style={{ marginTop: 16 }}>文件已上传成功</Title>
            <Paragraph>点击下方按钮开始AI内容检测</Paragraph>
            
            <Space>
              <Button 
                type="primary" 
                size="large" 
                onClick={handleStartDetection} 
                loading={detecting}
              >
                开始检测
              </Button>
              <Button 
                size="large" 
                onClick={() => {
                  setFileList([]);
                  setCurrentStep(0);
                  setUploadedTaskId(null);
                }}
              >
                重新上传
              </Button>
            </Space>
            
            {detecting && (
              <div style={{ marginTop: 20 }}>
                <Text>检测进度：</Text>
                <Progress percent={progress} status="active" />
              </div>
            )}
          </div>
        </Card>
      )}
      
      {currentStep === 2 && (
        <Card>
          <div style={{ textAlign: 'center' }}>
            <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a' }} />
            <Title level={4} style={{ marginTop: 16 }}>检测完成</Title>
            <Paragraph>论文检测已完成，点击下方按钮查看详细报告</Paragraph>
            
            <Space>
              <Button 
                type="primary" 
                size="large" 
                onClick={handleViewResult}
              >
                查看检测结果
              </Button>
              <Button 
                size="large" 
                onClick={() => {
                  setFileList([]);
                  setCurrentStep(0);
                  setUploadedTaskId(null);
                }}
              >
                检测新论文
              </Button>
            </Space>
          </div>
        </Card>
      )}
    </div>
  );
};

export default UploadPage; 