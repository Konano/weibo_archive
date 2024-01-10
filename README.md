# Weibo Archive

本项目是一个微博备份工具，可以将自己的微博账号的所有微博备份到本地，包括长文、图片、视频和评论。

## 使用说明

使用前需要将 `cookie_example.json` 重命名为 `cookie.json`，并填入自己的 cookie（注意需要使用 `m.weibo.cn` 的 cookie）

运行结束后 `ext` 和 `resources` 这两个文件夹连同 `posts.json` 就是所有数据了，请妥善保存。

### 如何找到自己的 Cookie？

1. 浏览器打开 https://m.weibo.cn/ ，登录自己的微博账号。
2. 按下 F12 打开开发者工具，切换到 Application/应用 选项卡。
3. 侧边栏找到左边 Cookie 选项，点击展开。
4. 找到 "SUB" 和 "SUBP"，将他们的值填入 `cookie.json` 中的 "SUB" 和 "SUBP" 字段。

![](doc/step.png)

### 我想重新备份自己的微博，应该怎么做呢？

删除 `cache` 文件夹，然后重新运行 `run.py` 即可。

## 局限性说明

#### 本项目只能备份自己的微博，不能备份别人的微博。

备份别人的微博可能会遇到各种限制，包括但不限于半年可见、仅粉丝可见、仅自己可见等等，无法完整备份。*（其实代码写了但是加了注释。）*

#### 本项目只能备份自己原创的微博的长文、图片、视频和评论，不支持备份转发的微博的长文和图片。

不是不可以，而是我觉得对我自己来说没有意义。*（其实代码也写了但是加了注释。）*

## TODO

- [x] 保存动态图片。
- [ ] 导出成 PDF 或者 MHTML。**[help_wanted]**
- [ ] 搞一个 Chrome 插件，可以在微博页面直接备份。**[help_wanted]**
