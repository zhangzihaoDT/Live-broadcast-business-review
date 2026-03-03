# Schema for 直播复盘表2026-02-27.xlsx

> Generated on: 2026-03-02 14:18:58

## Sheet: Sheet1

### 🕒 Time Dimension Analysis
- **Time Range:** 2026-02-01 08:00:00 to 2026-02-26 19:00:00
- **Granularity:** Sub-daily (Session/Hour)
- **Coverage:** 26 days (84 sessions)
- **Max Sessions/Day:** 6

### 📋 Data Structure
- **Rows:** 86
- **Columns:** 19

| Column Name | Data Type | Non-Null Count | Sample Value |
|---|---|---|---|
| 指标/场次 | str | 86 | 场均 |
| 全场景商机数 | float64 | 86 | 46.56 |
| 曝光人数 | float64 | 86 | 258503.3 |
| 场观 | float64 | 86 | 36475.42 |
| 曝光进入率 | str | 86 | 14.11% |
| 评论次数 | float64 | 86 | 873.51 |
| 人均观看时长 | str | 86 | 2分14秒 |
| 最高在线人数 | float64 | 86 | 851.44 |
| 涨粉量 | float64 | 86 | 99.4 |
| 直播时长 | str | 86 | 2时56分51秒 |
| 小风车点击次数 | float64 | 86 | 942.4 |
| 小风车点击率 | str | 86 | 2.04% |
| 互动率 | str | 86 | 3.66% |
| 关注率 | str | 86 | 0.27% |
| 互动次数 | float64 | 86 | 51911.61 |
| 点赞次数 | float64 | 86 | 51003.15 |
| 分享次数 | float64 | 86 | 34.94 |
| 加粉丝团人数 | float64 | 86 | 2.94 |
| 广告消耗 | float64 | 86 | 7819.62 |





# Schema for IM智己汽车 0201～0227.csv (Pivoted Wide Format)

> Generated on: 2026-03-02 14:53:10
> Note: Data was pivoted from Long to Wide format using '度量名称' as columns.

## File Content

### 🕒 Time Dimension Analysis
- **Date Column:** lc_create_time
- **Time Range:** 2022-05-23 01:09:00 to 2026-03-02 12:48:48
- **Granularity:** Sub-daily
- **Coverage:** 415 days (2989 records)
- **Max Records/Day:** 194

### 📋 Data Structure
- **Rows:** 2989
- **Columns:** 10

| Column Name | Data Type | Non-Null Count | Sample Value |
|---|---|---|---|
| lc_is_lock | int64 | 2989 | 0 |
| lc_user_phone_md5 | str | 2989 | 00222ff8013dad8de216266dd5812626 |
| lc_main_code | str | 2989 | M202602262150059964 |
| unique_clue_id | str | 2989 | 917615f8e5a844e68945180a417b01e4 |
| lc_small_channel_name | str | 2989 | IM智己汽车 |
| lc_create_time | str | 2989 | 2026/2/26 21:50:06 |
| lc_order_lock_time_min 年/月/日 | object | 2989 | -999999 |
| IM 顺位 | int64 | 2989 | 1 |
| Md5 Clue 总数 | int64 | 2989 | 1 |
| 唯一线索识别数 | int64 | 2989 | 1 |

