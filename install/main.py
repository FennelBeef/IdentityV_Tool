from smtplib import SMTP_SSL
from json import load,loads
from time import sleep
from pathlib import Path
from email.mime.text import MIMEText

from maa.toolkit import Toolkit
from maa.context import Context
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition
from plyer import notification

from infos import base_roi
from infos import ban_info
from infos import notice_info

#获取路径
main_path = Path.cwd()

def main():
    # 注册自定义识别器与动作
    Toolkit.pi_register_custom_recognition("Get_map",Get_map())
    Toolkit.pi_register_custom_recognition("Get_player",Get_player())
    Toolkit.pi_register_custom_recognition("Get_ban_info",Get_ban_info())
    
    Toolkit.pi_register_custom_action("Ban",Ban())
    Toolkit.pi_register_custom_action("Email_notice",Email_notice())
    Toolkit.pi_register_custom_action("Desktop_notice",Desktop_notice())

    # 启动 MaaPiCli
    Toolkit.pi_run_cli(f"{main_path}/res", f"{main_path}/debug", False)

class Get_map(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        roi_state = loads(argv.custom_recognition_param)["roi_state"]
        roi = get_roi_base_on_state(roi_state)
        
        Getmap_pipe = {"Get_map":{
                    "timeout": 3000,
                    "recognition": "OCR",
                    "roi": roi.roi_getmap,
                    "only_rec": True,
                    "expected": ["军工","军工厂","圣心医院","红教堂","湖景村","月亮河公园","里奥的回忆","永眠镇","唐人街","不归林"],
                    "replace": [["车","军"],["利","村"],["有","月"],["量","里"],["水","永"],["入","人"],["性","归"],["M","林"],
                                ["【",""],["】",""],["\\[",""],["\\]",""]]
                    }}
        
        rec_result = context.run_recognition("Get_map",argv.image,pipeline_override = Getmap_pipe)
        rec_result = rec_result.best_result.text
       
        #对特定识别结果的处理
        if rec_result == "军工":
            rec_result = "军工厂"
            
        print(f"地图：{rec_result}")
        context.override_pipeline({"检测阵营":{"custom_recognition_param": {"roi_state": roi_state,"map_info": rec_result}}})

        return CustomRecognition.AnalyzeResult(box=(),detail="")
    
class Get_player(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        map_info = loads(argv.custom_recognition_param)["map_info"]
        roi_state = loads(argv.custom_recognition_param)["roi_state"]
        
        roi = get_roi_base_on_state(roi_state)
        Getplayer_pipe = {"Get_player":{
                        "recognition": "OCR",
                        "roi": roi.roi_getplayer,
                        "only_rec": True}}

        rec_result = context.run_recognition("Get_player",argv.image,pipeline_override = Getplayer_pipe)
        player_info = rec_result.best_result.text
        print(f"禁选阵营：{player_info}")
        
        context.override_pipeline({"读取禁选信息":{"custom_recognition_param": {"roi_state": roi_state,"map_info": map_info,"player_info": player_info}}})
        
        return CustomRecognition.AnalyzeResult(box=(),detail="")
    

class Get_ban_info(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg) -> CustomRecognition.AnalyzeResult:
        
        infos = loads(argv.custom_recognition_param)
        roi_state = infos["roi_state"]
        map_info = infos["map_info"]
        player_info = infos["player_info"]

        with open (f"{main_path}/ban_config.json","r",encoding="utf-8") as f:
            data = load(f)[player_info]
 
            ban_details = data[map_info]
            ban1 = ban_details["ban1"]
            ban2 = ban_details["ban2"]

        if ban1 == "" and ban2 == "":
            ban_default = data["默认禁选"]
            ban_details = ban_default
            ban1 = ban_details["ban1"]
            ban2 = ban_details["ban2"]
            if ban1 != "" and ban2 !="":
                ban_details = [ban1,ban2]
            elif ban1 == "" and ban2 != "":
                ban1 = ban2
                ban_details = [ban1]
            elif ban1 != "" and ban2 == "":
                ban_details = [ban1]
        elif ban1 == "" and ban2 != "":
            ban1 = ban2
            ban_details = [ban1]
        elif ban1 != "" and ban2 == "":
            ban_details = [ban1]

        context.override_pipeline({"禁选角色":{"custom_action_param":{"roi_state": roi_state,"ban_details": ban_details}}})

        return CustomRecognition.AnalyzeResult(box=(),detail="")

class Ban(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        infos = loads(argv.custom_action_param)
        ban_details = infos["ban_details"]
        roi_state = infos["roi_state"]
        
        if len(ban_details) == 1:
            ban1 = ban_details[0]
            ban1_details = ban_info.ban_information[ban1]
            ban1_page = ban1_details["page"]

            ban1_side = ban1_details["page_side"]
            ban1_locaion = str(ban1_details["page_location"])
            ban1_roi = get_location_roi(ban1_side,ban1_locaion,roi_state)
            
            print(f"禁选信息：{ban1}")
            match ban1_page - 1:
                case 0:
                    pass
                case 1:
                    sleep(0.5)
                    context.run_pipeline("下一页")
                case 2:
                    sleep(0.5)
                    context.run_pipeline("下一页")
                    sleep(0.5)
                    context.run_pipeline("下一页")
                case _:
                    raise("角色配置文件异常，请联系开发者。")

            if ban1 != "厂长":
                context.override_pipeline({"Ban1":{
                                                "recognition": "TemplateMatch",
                                                "template": f"characters//{ban1}.png",
                                                "roi": ban1_roi,
                                                "action": "Click"}})
                context.run_pipeline("Ban1")
                context.run_pipeline("确认禁用")
            else:
                context.override_pipeline({"Ban1":{
                                                "recognition": "TemplateMatch",
                                                "template": ["characters//厂长.png",
                                                             "characters//厂长_月亮脸.png",
                                                             "characters//厂长_木偶比利.png",
                                                             "characters//厂长_地狱感知.png"],
                                                "roi": ban1_roi,
                                                "action": "Click"}})
                context.run_pipeline("Ban1")
                context.run_pipeline("确认禁用")

        elif len(ban_details) == 2:
            ban1 = ban_details[0]
            ban2 = ban_details[1]

            data = ban_info.ban_information
            ban1_details = data[ban1]
            ban2_details = data[ban2]
            ban1_page = ban1_details["page"]
            ban2_page = ban2_details["page"]
            ban1_side = ban1_details["page_side"]
            ban2_side = ban2_details["page_side"]
            ban1_locaion = ban1_details["page_location"]
            ban2_locaion = ban2_details["page_location"]
 
            #处理角色顺序问题
            if ban1_page > ban2_page:
                ban1_details,ban2_details = ban2_details,ban1_details
                ban1,ban2 = ban2,ban1
                ban1_page = ban1_details["page"]
                ban2_page = ban2_details["page"]
                
            if ban1_page == ban2_page and ban1_side == ban2_side and ban1_locaion > ban2_locaion:
                ban1_details,ban2_details = ban2_details,ban1_details
                ban1,ban2 = ban2,ban1
                ban1_page = ban1_details["page"]
                ban2_page = ban2_details["page"]
            print(f"禁选信息：{ban1} + {ban2}")
            
            #禁用第一名角色
            match ban1_page - 1:
                case 0:
                    pass
                case 1:
                    sleep(0.5)
                    context.run_pipeline("下一页")
                case 2:
                    sleep(0.5)
                    context.run_pipeline("下一页")
                    sleep(0.5)
                    context.run_pipeline("下一页")
                case _:
                    raise("角色配置文件异常，请联系开发者。")

            #获取 ban1 roi
            ban1_side = ban1_details["page_side"]
            ban1_locaion = str(ban1_details["page_location"])
            ban1_roi = get_location_roi(ban1_side,ban1_locaion,roi_state)

            if ban1 != "厂长":
                context.override_pipeline({"Ban1":{
                            "recognition": "TemplateMatch",
                            "template": f"characters//{ban1}.png",
                            "roi": ban1_roi,
                            "action": "Click",
                            "next": []}})
                context.run_pipeline("Ban1")
            else:
                context.override_pipeline({"Ban1":{
                                                "recognition": "TemplateMatch",
                                                "template": ["characters//厂长.png",
                                                             "characters//厂长_月亮脸.png",
                                                             "characters//厂长_木偶比利.png",
                                                             "characters//厂长_地狱感知.png"],
                                                "roi": ban1_roi,
                                                "action": "Click"}})
                context.run_pipeline("Ban1")
                
            #禁用第二名角色
            page_diff = ban2_page - ban1_page
            match page_diff:
                case 0:
                    pass
                case 1:
                    sleep(0.5)
                    context.run_pipeline("下一页")
                case 2:
                    sleep(0.5)
                    context.run_pipeline("下一页")
                    sleep(0.5)
                    context.run_pipeline("下一页")
                case _:
                    raise("角色配置文件异常，请联系开发者。")
                
            #获取 ban2 roi
            ban2_side = ban2_details["page_side"]
            ban2_locaion = str(ban2_details["page_location"])
            ban2_roi = get_location_roi(ban2_side,ban2_locaion,roi_state)
              
            context.override_pipeline({"Ban2":{
                                    "recognition": "TemplateMatch",
                                    "template": f"characters//{ban2}.png",
                                    "roi": ban2_roi,
                                    "action": "Click"}})
            context.run_pipeline("Ban2")       
            context.run_pipeline("确认禁用")

        else:
            raise("配置文件结构异常")
        
        return True

class Desktop_notice(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        infos = loads(argv.custom_action_param)
        title = infos["Title"]
        message = infos["Message"]

        notification.notify(title = title,
                     message = message,
                     timeout = 8)
        
        return True

class Email_notice(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        email_details = loads(argv.custom_action_param)
        Title = email_details["Title"]
        Body = email_details["Body"]

        with open (f"{main_path}/email_config.json","r",encoding="utf-8") as f:
            email_config = load(f)["email_config"]
            sender = str(email_config["Send_Address"])
            sender_password = str(email_config["Send_Password"])
            receiver = str(email_config["Receive_Address"])

            smtp_address = str(email_config["SMTP_Address"])
            smtp_port = int(email_config["SMTP_Port"])
            
        doctype = notice_info.email.doctype
        with_eamil = notice_info.email.with_eamil

        body = doctype + Body + with_eamil
        msg = MIMEText(body,"html","utf-8")
        msg["Subject"] = Title
        msg["From"] = sender
        msg["To"] = receiver

        smtp = SMTP_SSL(smtp_address,smtp_port)
        smtp.login(sender,sender_password)
        smtp.sendmail(sender,receiver,msg.as_string())
        smtp.quit()

        return True

def get_roi_base_on_state(roi_state:str):
    match roi_state:
        case "PC16_9":
            roi = base_roi.PC16_9
        case "Android16_9":
            roi = base_roi.Android16_9
        case _:
            raise("roi 声明参数异常，请联系开发者。")
        
    return roi

def get_location_roi(side:str,location:int|str,roi_state:str) -> list[int]:
    roi = get_roi_base_on_state(roi_state)
    
    side = str(side)
    location = str(location)

    ban_roi = roi.roi_location[side][location]

    return ban_roi


if __name__ == "__main__":
    main()