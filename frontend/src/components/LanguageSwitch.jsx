import React from 'react';
import { Button, Dropdown, Space } from 'antd';
import { GlobalOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const LanguageSwitch = ({ size = 'middle', type = 'default', style = {} }) => {
  const { i18n, t } = useTranslation();

  const currentLanguage = i18n.language;

  const handleLanguageChange = (language) => {
    i18n.changeLanguage(language);
  };

  const languageOptions = [
    {
      key: 'zh-CN',
      label: (
        <Space>
          <span>🇨🇳</span>
          <span>{t('language.chinese')}</span>
        </Space>
      ),
      onClick: () => handleLanguageChange('zh-CN')
    },
    {
      key: 'en-US',
      label: (
        <Space>
          <span>🇺🇸</span>
          <span>{t('language.english')}</span>
        </Space>
      ),
      onClick: () => handleLanguageChange('en-US')
    }
  ];

  const getCurrentLanguageLabel = () => {
    if (currentLanguage === 'zh-CN' || currentLanguage === 'zh') {
      return (
        <Space>
          <span>🇨🇳</span>
          <span>{t('language.chinese')}</span>
        </Space>
      );
    } else {
      return (
        <Space>
          <span>🇺🇸</span>
          <span>{t('language.english')}</span>
        </Space>
      );
    }
  };

  return (
    <Dropdown
      menu={{
        items: languageOptions,
        selectedKeys: [currentLanguage]
      }}
      placement="bottomRight"
      arrow
    >
      <Button 
        type={type} 
        size={size} 
        icon={<GlobalOutlined />}
        style={style}
      >
        {getCurrentLanguageLabel()}
      </Button>
    </Dropdown>
  );
};

export default LanguageSwitch; 