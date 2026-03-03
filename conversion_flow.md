# IM智己汽车 User Conversion Flow (Feb 2026 Cohort)

```mermaid
sankey-beta
    Global_Converters,IM_First_Touch,6
    Global_Converters,Other_First_Touch,10

    IM_First_Touch,IM_Last_Touch,3
    IM_First_Touch,Other_Last_Touch,3

    Other_First_Touch,IM_Last_Touch,1
    Other_First_Touch,Other_Last_Touch,9

    IM_Last_Touch,Direct_Lock,4

    Other_Last_Touch,Direct_Lock,2
    Other_Last_Touch,Other_Assisted,10
```

## Flow Analysis (Based on Refined Last Touch Logic)

```mermaid
graph TD
    Start[IM智己汽车 Cohort<br/>2112 Users] -->|99.2%| NonConv[Non-Converters<br/>2096 Users]
    Start -->|0.8%| A[Global Converters<br/>16 Users]

    A --> B{Entry Point?}
    B -->|IM First Touch: 6| C[IM Started Journey<br/>37.5%]
    B -->|Other First Touch: 10| D[IM Joined Mid-Stream<br/>62.5%]

    C --> E{Last Interaction<br/>Before Lock?}
    D --> E

    E -->|IM Last Touch: 4| F[IM was Closer<br/>25.0%]
    E -->|Other Last Touch: 12| G[Other Channel Closer<br/>75.0%]

    F -->|100%| H[Direct Lock<br/>IM Channel]

    G --> I{Attribution?}
    G -->|IM Direct: 2| H
    G -->|Other Assisted: 10| J[Assisted Lock<br/>Other Channel]

    style Start fill:#f9f,stroke:#333,stroke-width:2px
    style NonConv fill:#eee,stroke:#999,stroke-width:1px,stroke-dasharray: 5 5
    style A fill:#bbf,stroke:#333,stroke-width:2px
    style H fill:#bfb,stroke:#333,stroke-width:2px
    style F fill:#ff9,stroke:#333,stroke-width:2px
```

## 中英文术语对照表 (Terminology)

| 英文术语 (English Term)  | 中文术语 (Chinese Term) | 解释 (Explanation)                                                                                 |
| :----------------------- | :---------------------- | :------------------------------------------------------------------------------------------------- |
| **Cohort**               | 初始人群                | 本次分析选定的特定时间段（0201-0227）内新增的用户群体，共 2112 人。                                |
| **Global Converters**    | 全渠道锁单用户          | 在整个历史数据集中，无论通过哪个渠道，最终完成了锁单（Lock）的用户，共 16 人。                     |
| **Non-Converters**       | 未转化用户              | 在整个历史数据集中未产生锁单行为的用户。                                                           |
| **First Touch**          | 首次触点                | 用户在该品牌全生命周期中的第一次交互记录（最早的时间点）。                                         |
| **Last Touch**           | 末次触点                | 用户在产生“锁单”行为之前的最后一次交互记录（最晚的时间点，且必须早于锁单时间）。                   |
| **Direct Lock**          | 直接锁单                | 最终锁单归因于当前渠道（IM智己汽车），即该渠道是用户转化的直接来源。                               |
| **Assisted Lock**        | 辅助锁单                | 用户最终锁单了，但归因于其他渠道。当前渠道可能起到了辅助作用（如首次触点），但不是最终转化点。     |
| **Pivot (Long-to-Wide)** | 透视/转置（长改宽）     | 将原始数据中“一行一个度量”的长表格式，转换为“一行一个用户”的宽表格式，以便进行用户维度的聚合分析。 |
| **Data Sparse**          | 数据稀疏                | 指宽表中存在大量空值（NaN）的情况，例如并非所有用户都有锁单时间。                                  |
| **Attribution Logic**    | 归因逻辑                | 确定哪个渠道应该对用户的最终转化负责的规则（如：首次触点归因、末次触点归因）。                     |
