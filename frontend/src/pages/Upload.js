import React, { useState } from 'react';
import { Upload, Button, Typography, Card, Steps, Progress, Space, Alert, Spin } from 'antd';
import { 
  InboxOutlined, 
  FileTextOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { uploadApi, detectApi } from '../api/api';
import { showSuccess, showWarning, showError, notifySuccess, notifyError, notifyInfo } from '../utils/notification';

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
  const [detectingFiles, setDetectingFiles] = useState([]);
  const [statusMessage, setStatusMessage] = useState('');
  
  const navigate = useNavigate();

  const uploadProps = {
    name: 'file',
    multiple: false,
    fileList,
    beforeUpload: (file) => {
      // 检查文件类型
      const isValidType = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'].includes(file.type);
      if (!isValidType) {
        showError('只支持PDF、DOCX和TXT格式的文件！');
        return Upload.LIST_IGNORE;
      }
      
      // 检查文件大小 (50MB)
      const isValidSize = file.size / 1024 / 1024 < 50;
      if (!isValidSize) {
        showError('文件大小不能超过50MB！');
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
      showWarning('请先选择要上传的文件！');
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
      
      console.log('Upload result:', result);
      
      // 验证任务ID
      if (!result || !result.task_id) {
        throw new Error('上传成功但未返回有效的任务ID');
      }
      
      if (typeof result.task_id !== 'string') {
        console.error('Server returned non-string task ID:', result.task_id);
        // 尝试转换为字符串
        const stringTaskId = String(result.task_id);
        console.log('Converted task ID to string:', stringTaskId);
        setUploadedTaskId(stringTaskId);
      } else {
        setUploadedTaskId(result.task_id);
      }
      
      setCurrentStep(1);
      showSuccess('文件上传成功！');
    } catch (error) {
      console.error('上传失败:', error);
      setError('文件上传失败：' + (error.response?.data?.detail || error.message || '请稍后再试'));
    } finally {
      setUploading(false);
    }
  };

  const handleStartDetection = async (taskId = uploadedTaskId, fileIndex = null) => {
    if (!taskId) {
      setError('任务ID不存在，请先上传文件');
      return;
    }
    
    if (typeof taskId !== 'string') {
      console.error('Invalid task ID type:', typeof taskId, taskId);
      setError('任务ID类型错误，请重新上传文件');
      return;
    }
    
    console.log('Starting detection for task ID:', taskId);
    
    setDetecting(true);
    setError(null);
    
    try {
      // 开始检测
      await detectApi.startDetection(taskId);
      
      // 显示开始检测的通知
      notifyInfo('检测已开始', '系统正在分析您的文档...');
      setStatusMessage('检测任务已启动，正在准备文档分析...');
      
      // 如果是批量检测中的一个文件，更新文件状态
      if (fileIndex !== null) {
        const updatedFiles = [...detectingFiles];
        updatedFiles[fileIndex] = {
          ...updatedFiles[fileIndex],
          status: 'detecting'
        };
        setDetectingFiles(updatedFiles);
      }
      
      // 检测进度轮询
      setProgress(0);
      let progressInterval = setInterval(() => {
        // 只有在status不是completed或failed时才更新进度
        setProgress((prev) => {
          // 确保进度不会超过90%，保留给最终完成阶段
          if (prev >= 90) {
            return 90;
          }
          // 每次增加一个随机值1-3之间，使进度看起来更自然
          const increment = 1 + Math.floor(Math.random() * 3);
          return prev + increment;
        });
      }, 2000);
      
      // 轮询检测状态
      let statusCheckInterval = setInterval(async () => {
        try {
          console.log('检查任务状态:', taskId);
          const result = await detectApi.getDetectionStatus(taskId);
          console.log('获取到的任务状态:', result.status, '任务结果:', result);
          
          // 始终更新进度，确保UI响应
          let newProgress = progress;
          
          // 更新进度显示（根据状态调整进度显示）
          if (result.status === 'processing') {
            // 确保进度条显示处理中的动态效果
            if (progress < 30) {
              newProgress = Math.min(progress + 5, 30);
              setProgress(newProgress);
              setStatusMessage('正在提取文档内容，准备进行AI分析...');
              console.log('更新进度到:', newProgress, '阶段: 文档提取');
            } else if (progress < 60) {
              newProgress = Math.min(progress + 3, 60);
              setProgress(newProgress);
              setStatusMessage('AI模型正在分析文档内容，检测AI生成特征...');
              console.log('更新进度到:', newProgress, '阶段: AI分析');
            } else if (progress < 90) {
              newProgress = Math.min(progress + 2, 90);
              setProgress(newProgress);
              setStatusMessage('正在生成分析报告，即将完成...');
              console.log('更新进度到:', newProgress, '阶段: 生成报告');
            }
          }
          
          if (result.status === 'completed') {
            console.log('检测完成, 清理轮询');
            clearInterval(statusCheckInterval);
            clearInterval(progressInterval);
            setProgress(100);
            setStatusMessage('检测已完成！即将跳转到结果页面...');
            console.log('检测已完成！更新进度到100%，准备导航到结果页面');
            
            // 如果是批量检测中的一个文件，更新文件状态
            if (fileIndex !== null) {
              const updatedFiles = [...detectingFiles];
              updatedFiles[fileIndex] = {
                ...updatedFiles[fileIndex],
                status: 'completed'
              };
              setDetectingFiles(updatedFiles);
              notifySuccess('检测完成', `文件 "${updatedFiles[fileIndex].name}" 检测已完成`);
            } else {
              setCurrentStep(2);
              showSuccess('检测完成！');
              
              // 在1秒后重置状态并导航到结果页面
              setTimeout(() => {
                setDetecting(false);
                // 导航到结果页面
                console.log('即将导航到结果页面:', `/result/${taskId}`);
                navigate(`/result/${taskId}`);
              }, 1000);
            }
          } else if (result.status === 'failed') {
            console.log('检测失败, 清理轮询');
            clearInterval(statusCheckInterval);
            clearInterval(progressInterval);
            setStatusMessage('检测失败，请重试！');
            console.log('检测失败，停止轮询和进度条');
            
            // 如果是批量检测中的一个文件，更新文件状态
            if (fileIndex !== null) {
              const updatedFiles = [...detectingFiles];
              updatedFiles[fileIndex] = {
                ...updatedFiles[fileIndex],
                status: 'failed'
              };
              setDetectingFiles(updatedFiles);
              notifyError('检测失败', `文件 "${updatedFiles[fileIndex].name}" 检测失败`);
            } else {
              setError('检测失败，请重试！');
              // 设置detecting为false
              setDetecting(false);
            }
          } else {
            console.log('任务仍在处理中，继续轮询');
          }
        } catch (error) {
          console.error('获取检测状态失败:', error);
          clearInterval(statusCheckInterval);
          clearInterval(progressInterval);
          setStatusMessage('获取检测状态失败，请刷新页面重试');
          
          // 如果是批量检测中的一个文件，更新文件状态
          if (fileIndex !== null) {
            const updatedFiles = [...detectingFiles];
            updatedFiles[fileIndex] = {
              ...updatedFiles[fileIndex],
              status: 'failed'
            };
            setDetectingFiles(updatedFiles);
            notifyError('检测状态获取失败', `文件 "${updatedFiles[fileIndex].name}" 状态获取失败`);
          } else {
            setError('获取检测状态失败，请刷新页面重试');
            // 设置detecting为false
            setDetecting(false);
          }
        }
      }, 2000); // 减少轮询间隔为2秒
      
    } catch (error) {
      console.error('开始检测失败:', error);
      
      // 如果是批量检测中的一个文件，更新文件状态
      if (fileIndex !== null) {
        const updatedFiles = [...detectingFiles];
        updatedFiles[fileIndex] = {
          ...updatedFiles[fileIndex],
          status: 'failed'
        };
        setDetectingFiles(updatedFiles);
        notifyError('检测启动失败', `文件 "${updatedFiles[fileIndex].name}" 检测启动失败`);
      } else {
        setError('开始检测失败：' + (error.response?.data?.detail || '请稍后再试'));
      }
    }
  };
  
  const handleViewResult = () => {
    navigate(`/result/${uploadedTaskId}`);
  };

  // eslint-disable-next-line no-unused-vars
  const handleStartAllDetection = async () => {
    const uploadedFiles = detectingFiles.filter(file => file.status === 'uploaded');
    
    if (uploadedFiles.length === 0) {
      showWarning('没有可检测的文件');
      return;
    }
    
    notifyInfo('批量检测开始', `开始检测 ${uploadedFiles.length} 个文件`);
    
    for (let i = 0; i < uploadedFiles.length; i++) {
      const file = uploadedFiles[i];
      const index = detectingFiles.findIndex(item => item.taskId === file.taskId);
      
      if (index !== -1) {
        await handleStartDetection(file.taskId, index);
        // 添加短暂延时，避免同时发起太多请求
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
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
                onClick={() => handleStartDetection(uploadedTaskId)} 
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
                <Progress percent={progress} status="active" format={percent => `${percent}%`} />
                <div style={{ marginTop: 10, textAlign: 'center' }}>
                  <Spin spinning={true} size="small" style={{ marginRight: 8 }} />
                  <Text strong>{statusMessage || '正在进行AI内容检测，这可能需要1-2分钟...'}</Text>
                  <br />
                  <Text type="secondary">系统状态: <Text type="warning">处理中</Text> (请勿关闭页面)</Text>
                </div>
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