from typing import Dict
from funcguard import print_line


class ResponseError( Exception ) :
    def __init__( self, platform: str, model_name: str, exception: BaseException, error_tag: str ) :
        self.platform = platform
        self.model_name = model_name
        # 当前的模型信息
        self.base_model_info = f"Model {self.platform} : {self.model_name}"

        self.original_exception = exception
        self.error_tag = error_tag
        self.error_message = ""

        self.reported = False  # 是否已打印报错信息
        self.skip_report = False  # 是否跳过打印报错信息

        super().__init__( str( exception ) )  # 调用父类构造


    def __str__( self ) :
        # 确保抛出时显示有用的错误信息
        return self.error_message or str( self.original_exception )


    # 打印报错信息
    def report_error( self, print_tag = True, print_detail = False ) :
        if self.skip_report or self.reported :
            return

        print_line()
        print( self.base_model_info )

        if print_tag and self.error_tag :
            print( self.error_tag )
        if print_detail :
            print( self.error_message )

        self.reported = True


    # 构建报错信息
    def _build_error_message( self, error_info: Dict ) -> str :
        """构建错误消息字符串

        参数:
            error_data: 包含错误信息的数据字典
            original_exception: 原始异常对象，用于备用错误消息

        返回:
            格式化后的错误消息字符串
        """
        error = error_info.get( "error", { } )
        message = error_info.get( "message", "" )

        if isinstance( error, str ) :
            message = error
        else :
            # 如果没有message，尝试从error中获取
            if not message :
                message = error.get( "message", "" )

        # 构建基础错误消息
        if message :
            error_parts = [ f"message: {message}" ]
        else :
            error_parts = [ str( self.original_exception ) ]

        if not isinstance( error, str ) :
            metadata = error.get( "metadata", { } )  # openrouter
            raw = metadata.get( "raw", "" )
            provider_name = metadata.get( "provider_name", "" )

            # 只在有值时添加provider信息
            if provider_name :
                error_parts.append( f"provider: {provider_name}" )

            # 只在有值时添加detail信息
            if raw :
                error_parts.append( f"detail: {raw}" )

        return " , ".join( error_parts )


    # 提取错误信息
    def extract_error_message( self ) -> str :
        """提取错误信息"""
        error_info = { }
        response = getattr( self.original_exception, 'response', None )

        # 如果异常对象本身就是 response
        if hasattr( self.original_exception, 'model_dump' ) :
            response = self.original_exception

        if hasattr( response, 'model_dump' ) :  # 兼容 openai
            error_info = response.model_dump() # type: ignore

        # hasattr 检查 response 是否有 json 方法
        elif hasattr( response, 'json' ) :
            error_info = response.json() # type: ignore
            # 判断 res 是否是列表
            if isinstance( error_info, list ) :
                e_info = error_info[ 0 ]
                if e_info and isinstance( e_info, dict ) :
                    error_info = e_info

        if not isinstance( error_info, dict ) :
            error_info = { }

        error_message = self._build_error_message( error_info )
        self.error_message = error_message

        return error_message


    # 重新提取错误信息
    def get_error_message( self ) :

        if self.error_message :
            return self.error_message

        return self.extract_error_message()
