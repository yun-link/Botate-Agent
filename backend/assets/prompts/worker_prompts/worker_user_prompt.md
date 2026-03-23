<task>
{task}
</task>

<workspace>
<workspace_path>
{workspace_path}
所有文件操作（读取、写入、编辑）使用相对路径时，均以此工作空间目录为根目录。请使用绝对路径或相对于此目录的路径来操作文件。
当开发具体项目时请在具体的文件夹下进行，例如当用户要求开发一个项目时应该在./project-name/下，而不是直接使用./。
</workspace_path>
<workspace_files>
{workspace_path}
</workspace_files>
<workspace>

<skills_list>
以下是你可以使用的技能。根据任务需求，使用 `skill` 工具加载合适的技能：

{skills_list}
</skills_list>

<os>
当前的操作系统是：{os}
</os>

<time>
当前的时间是：{time}
</time>

## 使用说明

1. 首先分析上述任务的具体需求
2. 从可用技能列表中选择最合适的技能
3. 使用 `skill(skill_name="技能名称")` 加载技能
4. 根据加载的技能指导执行任务
5. 完成任务后输出 `[任务结束]` 标记

请开始执行任务。
