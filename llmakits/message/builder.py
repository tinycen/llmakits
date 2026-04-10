"""
消息构建器
负责根据不同提供商的要求构建消息格式
"""

from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from filekits.base_io import download_encode_base64, batch_download_encode_base64
from .validator import validate_base64_content, detect_base64_image_mime_type
from ..utils.normalize_error import ResponseError


def prepare_messages(
        provider_name: str,
        system_prompt: str,
        user_text: str,
        include_img: bool = False,
        img_list: Optional[ List[ str ] ] = None,
) -> List[ Dict[ str, Any ] ] :
    """
    根据提供商名称准备消息格式

    Args:
        provider_name: 提供商名称 ('dashscope', 'zhipu', 'openai', 'modelscope', 'ollama')
        system_prompt: 系统提示词
        user_text: 用户文本
        include_img: 是否包含图片
        img_list: 图片URL列表

    Returns:
        格式化后的消息列表
    """
    if img_list is None :
        if include_img :
            error_tag = "缺少图片"
            response_error = ResponseError( "", "",
                                            exception = ValueError( "包含图片的消息，图片 img_list 不能为空。" ),
                                            error_tag = error_tag )
            response_error.skip_report = True
            raise response_error

        img_list = [ ]

    if include_img and len( img_list ) < 1 :
        error_tag = "缺少图片"
        response_error = ResponseError( "", "",
                                        exception = ValueError( "包含图片的消息，图片 img_list 不能为空。" ),
                                        error_tag = error_tag )
        response_error.skip_report = True
        raise response_error

    # 根据提供商构建不同格式的消息
    system_content, user_content = _build_content_by_provider(
        provider_name, system_prompt, user_text, include_img, img_list
    )

    # 构建消息结构
    user_message = { "role" : "user", "content" : user_content }

    if system_content :
        system_message = { "role" : "system", "content" : system_content }
        return [ system_message, user_message ]
    else :
        return [ user_message ]


def rebuild_messages_single_image(
        provider_name: str,
        system_prompt: str,
        user_text: str,
        reject_single_image: bool,
        img_list: list,
) -> List[ Dict[ str, Any ] ] :
    """
    重新构造messages，只使用一张图片。

    Args:
        provider_name: 提供商名称
        system_prompt: 系统提示词
        user_text: 用户文本
        reject_single_image: 是否禁止单张图片（为True时若图片数量为1则抛异常）
        img_list: 图片URL或base64列表

    Returns:
        格式化后的消息列表（仅保留一张图片）

    Notes:
        优先选择已转换成功的base64图片；如果没有，则回退到第一张图片。
        这样在重试阶段可以尽量保留已经成功转换的图片，而不是再次发送原始URL。
    """
    if not img_list :
        error_tag = "缺少图片"
        response_error = ResponseError( "", "",
                                        exception = ValueError( "包含图片的消息，图片 img_list 不能为空。" ),
                                        error_tag = error_tag )
        response_error.skip_report = True
        raise response_error

    img_num = len( img_list )

    if reject_single_image :
        if img_num == 1 :
            error_tag = "图片数量 == 1，无法缩减"
            response_error = ResponseError( "", "",
                                            exception = ValueError( "异常：图片数量 == 1，无法缩减" ),
                                            error_tag = error_tag )
            response_error.skip_report = True
            raise response_error

    selected_img = next(
        (img for img in img_list if isinstance( img, str ) and img.startswith( 'data:image/' ) and ';base64,' in img),
        img_list[ 0 ],
    )

    return prepare_messages( provider_name, system_prompt, user_text, True, [ selected_img ] )


def _build_content_by_provider(
        provider_name: str,
        system_prompt: str,
        user_text: str,
        include_img: bool,
        img_list: List[ str ],
        image_cache = None,  # 图片缓存参数
) -> tuple :
    """根据提供商构建内容格式"""

    if not include_img :
        return system_prompt, user_text

    if provider_name == "dashscope" :
        user_content = [ { "image" : img } for img in img_list ]
        user_content.append( { "text" : user_text } )
        if system_prompt :
            system_content = [ { "text" : system_prompt } ]
        else :
            system_content = [ ]

    elif provider_name == "ollama" :
        if system_prompt :
            system_content = system_prompt
        else :
            system_content = [ ]
        user_content = user_text
        try :
            # todu 这里后续需要修改
            img_list = batch_download_encode_base64( img_list )
        except Exception as e :
            print( f"Ollama图片批量转换base64失败: {e}" )
            raise Exception( f"图片下载或转换base64失败，url：{img_list}" )

    # 兼容通用的 "openai", "modelscope", "openrouter" 格式 , 不支持 zhipu ( 可切换为 zhipu_openai 进行兼容 )
    else :
        if provider_name in [ "openrouter", "gemini", "vercel", "github" ] :
            # openrouter 需要base64格式的图片
            img_list = convert_images_to_base64( img_list, image_cache )  # 传递缓存

        user_content = [ { "type" : "image_url", "image_url" : { "url" : img } } for img in img_list ]
        if provider_name in [ "gitcode" ] :
            if system_prompt :
                system_prompt_user = f"# 任务角色与设定 \n{system_prompt}\n"
            else :
                system_prompt_user = ""
            user_prompt = f"# 任务相关信息 \n{user_text}\n"
            user_content.append( { "type" : "text", "text" : system_prompt_user + user_prompt } )
            system_content = [ ]
        else :
            user_content.append( { "type" : "text", "text" : user_text } )
            if system_prompt :
                system_content = [ { "type" : "text", "text" : system_prompt } ]
            else :
                system_content = [ ]

    return system_content, user_content


def _infer_mime_type_from_url( img_url: str ) -> str :
    """根据URL路径后缀推断图片MIME类型。"""
    ext_to_mime = {
        ".jpg"  : "image/jpeg",
        ".jpeg" : "image/jpeg",
        ".png"  : "image/png",
        ".gif"  : "image/gif",
        ".webp" : "image/webp",
        ".bmp"  : "image/bmp",
        ".svg"  : "image/svg+xml",
        ".avif" : "image/avif",
        ".heic" : "image/heic",
        ".heif" : "image/heic",
    }
    img_path = urlparse( img_url ).path.lower()
    for ext, mime_type in ext_to_mime.items() :
        if img_path.endswith( ext ) :
            return mime_type
    return ""


def _build_base64_image_url( base64_str: str, img_url: str = "" ) -> str :
    """根据base64内容或URL推断MIME类型并构造data URL。"""
    mime_type = detect_base64_image_mime_type( base64_str ) or _infer_mime_type_from_url( img_url ) or "image/jpeg"
    return f"data:{mime_type};base64,{base64_str}"


def convert_images_to_base64( img_list: List[ str ], image_cache = None ) -> List[ str ] :
    """
    将图片列表转换为base64格式，并保持输出列表与输入列表一一对应。

    Args:
        img_list: 图片URL或base64列表
        image_cache: 可选的图片base64缓存对象

    Returns:
        与输入顺序一致的图片列表。
        - 转换成功的项会变成 `data:image/...;base64,...`
        - 转换失败的项会保留原始URL，便于上层决定是否继续重试

    Notes:
        1. 不再仅依赖 `.jpg/.jpeg/.png` 后缀判断是否可转换；
        2. 转换后的图片列表，不支持 sdk/platform/provider = zhipu ，
           如需使用，请使用名称 zhipu_openai 兼容 openai 的格式。
    """
    if not img_list :
        raise ValueError( "图片 img_list 不能为空!" )

    # 如果没有传入缓存对象，尝试从 dispatcher 获取全局缓存。
    # 注意：这里必须在函数内导入，避免和 dispatcher 形成循环引用。
    if image_cache is None :
        try :
            from ..dispatcher import ModelDispatcher

            image_cache = ModelDispatcher.get_image_cache()
        except ImportError :
            # 如果无法导入，不使用缓存。
            image_cache = None

    processed_img_list = [ ]
    successful_conversions = 0

    for img_url in img_list :
        # 始终保持输出列表与输入列表等长，避免上层按位置回填时发生错位。
        if not isinstance( img_url, str ) :
            # processed_img_list.append(img_url)
            continue
        # 如果已经是 通过 _build_base64_image_url 构建好的 base64 格式 ，就直接添加
        if img_url.startswith( 'data:image/' ) and ';base64,' in img_url :
            processed_img_list.append( img_url )
            successful_conversions += 1
            continue

        normalized_img_url = img_url.strip()
        if not normalized_img_url :
            processed_img_list.append( img_url )
            continue

        if image_cache is not None :
            # 先查缓存，减少重复下载。
            cached_base64 = image_cache.get( normalized_img_url )
            if cached_base64 :
                is_valid, error_msg = validate_base64_content( cached_base64, expected_type = "image" )
                if is_valid :
                    print( f"已从缓存中获取图片base64: {normalized_img_url}" )
                    processed_img_list.append( _build_base64_image_url( cached_base64, normalized_img_url ) )
                    successful_conversions += 1
                    continue
                print( f"缓存中的base64内容无效，已跳过: {normalized_img_url}, 原因: {error_msg}" )

        try :
            # 不依赖URL后缀，直接按URL下载并探测真实内容类型。
            base64_str = download_encode_base64( normalized_img_url )
            if not base64_str :
                print( f"转换后, base64_str 为空，: {normalized_img_url}" )
                # processed_img_list.append(img_url)
                continue

            is_valid, error_msg = validate_base64_content( base64_str, expected_type = "image" )
            if not is_valid :
                print( f"转换后，base64 验证失败，已跳过: {normalized_img_url}, 原因: {error_msg}" )
                # processed_img_list.append(img_url)
                continue

            if image_cache is not None :
                image_cache.put( normalized_img_url, base64_str )

            processed_img_list.append( _build_base64_image_url( base64_str, normalized_img_url ) )

            successful_conversions += 1
            print( f"已将图片转换为base64格式: {normalized_img_url}" )

        except Exception as e :
            print( f"图片下载转base64失败: {normalized_img_url}\n{e}" )
            # processed_img_list.append(img_url)

    if successful_conversions == 0 :
        error_tag = "图片下载转base64失败"
        exception = Exception( f"所有图片 下载/转换base64 均失败，url：{img_list}" )
        response_error = ResponseError( "", "",
                                        exception = exception,
                                        error_tag = error_tag )
        response_error.skip_report = True
        raise response_error

    return processed_img_list


def prepare_request_data( platform: str, messages: Any, message_info: Optional[ Dict ] ) -> Tuple[ Any, Dict ] :
    """准备请求数据

    Args:
        platform: 平台名称
        messages: 请求消息对象
        message_info: 消息信息字典，包含系统提示词、用户文本、是否包含图片和图片列表等

    Returns:
        Tuple[Any, Dict]: (更新后的消息对象, 消息配置字典)
    """
    message_config = { "user_text" : "", "include_img" : False, "img_list" : [ ] }

    if message_info is not None :
        message_config.update(
            {
                "user_text"   : message_info[ "user_text" ],
                "include_img" : message_info.get( "include_img", False ),
                "img_list"    : message_info.get( "img_list", [ ] ),
            }
        )

        system_prompt = message_info[ "system_prompt" ]
        if system_prompt :
            message_config[ "system_prompt" ] = system_prompt

        messages = prepare_messages(
            platform,
            message_config.get( "system_prompt", "" ),
            message_config[ "user_text" ],
            message_config[ "include_img" ],
            message_config[ "img_list" ],
        )
    return messages, message_config
