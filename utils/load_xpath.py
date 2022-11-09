# 登陆相关
xpath_switch_icon = "//span[contains(@class,'switch-icon')]"
xpath_service_policy = "//div[@class='terms-and-policy-container']//input"
xpath_input_mobile_phone = "//input[@class='mobile-input-phone']"
xpath_confirm_phone = "//button[@data-test='login-phone-next-btn']"
xpath_switch_pw_login = "//button[text()='密码登录']"
xpath_pw_input = "//div[contains(@class,'verify-credential-pwd-input')]//input[@name='password_input']"
xpath_confirm_pw = "//button[@data-test='login-pwd-next-btn']"

# 触发上传相关
xpath_page_title = "//div[@class='page-title']"
xpath_upload_button_div = "//div[@class='upload-menu-button']"
xpath_upload_body = "//div[@class='upload-modal-body']"
xpath_upload_submit = "//button[text()='提交']"
xpath_upload_menu_container = "//div[@class='upload-menu-container']"
xpath_upload_modal_body = "//div[@class='upload-modal-body']"
xpath_upload_button = "//button[contains(@class,'upload-button')]"

# 上传后状态检查相关
xpath_videos = "//div[contains(@class,'meeting-list-item-wrapper')]"
xpath_video_title = ".//div[@class='content']/text()"
xpath_video_url = "./a/@href"
xpath_video_duration = ".//div[@class='meeting-list-item-duration']/text()"
xpath_video_video_transcoding = ".//div[@class='meeting-status-loading']/text()"
xpath_upload_status = "//div[@class='upload-status']//text()"

# 详情页相关
xpath_detail_menu = "//div[contains(@class,'detail-meeting-menu')]"
xpath_srt_option = "//span[text()='SRT']"
xpath_format_selector = "//div[text()='飞书文档']"
xpath_export_miaoji = "//div[text()='导出妙记']"
xpath_delete_miaoji = "//div[text()='删除']"
xpath_detail_option = "//div[@class='detail-meeting-menu-btn']"
xpath_button_export = "//button[text()='导出']"
xpath_button_delete = "//button[text()='删除']"
