import os
from filekits.base_io import StrPath


def load_prompt( file_path : StrPath ) -> str :
    """从指定路径读取并返回 prompt 文件内容"""
    with open( file_path , 'r' , encoding = 'utf-8' ) as file :
        return file.read()


class PromptManager :
    """
    Prompt 管理器，用于加载和管理 prompt 模板文件

    :param base_folder: 存放 prompt 文件的基础文件夹路径
    :param subfolder_name: 可选的子文件夹名称。
        - 用于加载特定子文件夹下的 prompt，
        - 为 None 时仅加载 General 文件夹
    """
    def __init__( self , base_folder : StrPath , subfolder_name : str | None = None ) :

        if subfolder_name is None:
            subfolder_name = ""

        self.subfolder_name = subfolder_name
        self.base_folder = base_folder
        self.prompts_content = { }

        prompts_folders = [ ]

        general_folder = os.path.join( self.base_folder , 'General' )
        if os.path.isdir( general_folder ) :
            prompts_folders.append( general_folder )

        if self.subfolder_name :
            subfolder_path = os.path.join( self.base_folder , self.subfolder_name )
            if os.path.isdir( subfolder_path ) :
                prompts_folders.append( subfolder_path )

        for folder in prompts_folders :
            for filename in os.listdir( folder ) :
                if filename.endswith( '.md' ) :
                    file_path = os.path.join( folder , filename )
                    key = os.path.splitext( filename )[ 0 ]
                    if key in self.prompts_content :
                        raise KeyError( f"Duplicate prompt key '{key}' " )
                    self.prompts_content[ key ] = load_prompt( file_path )

        self.prompts_key = list( self.prompts_content.keys() )

    def get_prompt( self , prompt_key : str ) -> str :
        """
        根据 key 获取对应的 prompt 内容

        :param prompt_key: prompt 文件名（不含扩展名）
        :return: prompt 文件内容
        :raises KeyError: 当指定的 key 不存在时抛出异常
        """
        if prompt_key not in self.prompts_content :
            raise KeyError( f"Prompt with key '{prompt_key}' not found." )
        return self.prompts_content[ prompt_key ]
