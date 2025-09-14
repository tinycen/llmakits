import re
import json

# 移除 think 段落
def remove_think_section( text ) :
    start_tag = '<think>'
    if start_tag not in text :
        return text

    end_tag = '</think>'

    start_index = text.find( start_tag )
    end_index = text.find( end_tag )

    if start_index != -1 and end_index != -1 :
        # Ensure the end index is after the start index
        end_index += len( end_tag )
        return text[ :start_index ] + text[ end_index : ]
    else :
        return text


# 用于从字符串中提取第一个有效的JSON内容
def extract_json_from_string( text_with_json: str ) -> str | None :
    """
    从包含JSON内容的字符串中提取JSON字符串，优先匹配```json ... ```代码块。
    参数:
        text_with_json (str): 包含JSON内容的字符串。
    返回:
        str: 提取到的JSON字符串，如果未找到或无效则返回None。
    """
    # 优先查找```json ... ```代码块
    match = re.search( r"```json\s*(\{[\s\S]*?\})\s*```", text_with_json )
    if match :
        json_string = match.group( 1 ).strip()
        try :
            json.loads( json_string )
            return json_string
        except json.JSONDecodeError :
            print( f"警告: 提取到的```json代码块内容不是有效的JSON: {json_string}" )
            return None
    raise ValueError( "未找到有效的JSON代码块" )


# 响应结果转json
def convert_to_json( text ) :
    text = remove_think_section( text )
    text = text.strip()
    try :
        if text.startswith( "```json" ) :
            text = text.strip( "```json\n" )
        try :
            return json.loads( text )
        except :
            return eval( text )
    except :
        # 新增：尝试用 extract_json_from_string 提取
        extracted_json = extract_json_from_string( text )
        if extracted_json :
            return json.loads( extracted_json )
        print( "无法解析为json格式:" )
        print( text )
        raise Exception( "无法解析为json格式" )


# 将响应结果转为json，并获取其中的指定字段
def extract_field( message, *target_fields ) :
    """
    示例用法：

    # 提取单个字段
    field_1 = extract_field(message, "field_1")

    # 提取多个字段
    field_1, field_2 = extract_field(message, "field_1", "field_2")

    """

    if isinstance( message, dict ) :
        result = message
    else :
        result = convert_to_json( message )

    try :
        if len( target_fields ) == 1 :
            return result[ target_fields[ 0 ] ]  # 只有一个字段时，直接返回该字段的值
        return tuple( result[ field ] for field in target_fields )  # 多个字段时，返回元组
    except KeyError as e :
        raise KeyError( f"字段 {e} 不存在于消息中" ) from e