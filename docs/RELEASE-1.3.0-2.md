# LetMeBlock 1.3.0-2 · Native RootHide 正式重编发行

## 授权与基线
用户明确要求将自己的RootHide原生LetMeBlock依赖包重新编译为纯数字正式版本并发布到doimty.github.io。基线`3b4057d3e293ca4fc96a7d1bafb29a386a300bb9`（1.3.0-1+native1）。新分支`release/letmeblock-1.3.0-2`，仅推到doimty/LetMeBlock，保留上游/master及旧测试分支不改。正式版本`1.3.0-2`，dpkg必须高于旧测试版与原源内1.3.0。

只编译本依赖包，官方libSandy保持预编译引用，不重编/打包/发布它。Tweak.xm、include、filter、profile、maintainer脚本、固定工具链全部逐字节冻结。Package保持com.ps.letmeblock/iphoneos-arm64e/min15，保留PoomSmart作者和MIT声明；网页明确这是重编发行，不冒充上游发布或自研hook。

## 打包根因修正
静态检查旧native1 deb发现数字tar UID/GID为501/20（不是root）；不能凭tar名字root判定。新正式包用dpkg --root-owner-group规范，前后data/control每个entry类型/mode/content哈希完全相同才接受。真实验证器拒绝非0:0属主，含目录。新增三组UID/GID负例与版本升级顺序测试。该改动不改任何运行逻辑；安装/卸载时原脚本的DNS重启动作仍存在，本轮不执行。

## 发布与验收
- 本地原套件+新增root归档/版本测试及重打正反；提交元数据门禁逐SHA。
- GitHub Actions Apple编译与实包API/路径/架构/minOS/签名blob等门禁；本地独立代码页与数字属主检查，source/run/deb/artifact SHA对应。
- APT从当前main ade9c277隔离worktree/新release分支正常PR合并发布；新增正式包、索引、源代码归档、描述页/图标。用户未要求删除旧包，保留旧LetMeBlock，所有无关包及索引stanza字节不改，历史异常段保留。
- Packages/gz/xz/lzma/Release/deb/source/icon/depiction线上HTTP200与提交逐字节核验。Pages与源发布不等于手机安装、PAC/沙盒/真实DNS/能耗或rootless验收。

## QuietHosts 与 rootless
QH公开依赖描述仅列LetMeBlock/libSandy及对应越狱环境，不固定版本文本。当前包仍RootHide专用；rootless必须独立构建路径/根目录锚点/依赖变体与真机门禁，不可仅改scheme或删除RootHide文案就称支持。QH Havoc上架/定价属后续计划，不在本次发布范围内。
