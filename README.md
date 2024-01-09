# Weibo Archive

## 说明

本项目是一个微博备份工具，可以将自己的微博账号的所有微博备份到本地，包括长文、图片、视频和评论。

使用前需要将 `cookie_example.json` 重命名为 `cookie.json`，并填入自己的 cookie（注意需要使用 `m.weibo.cn` 的 cookie）

运行结束后 `ext` 和 `resources` 这两个文件夹连同 `posts.json` 就是所有数据了，请妥善保存。

## TODO

- [ ] 保存转发的微博内容，包括长文和图片。
- [ ] 保存动态图片（我自己的微博没有这种例子，所以没能测试到）。
