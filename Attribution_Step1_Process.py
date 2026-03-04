import pandas as pd
import os
import sys

def process_attribution_matrix(input_file, output_file):
    """
    处理渠道归因矩阵数据，生成包含锁单数和助攻数的宽表。
    
    Args:
        input_file (str): 输入文件路径 (UTF-16, Tab分隔)
        output_file (str): 输出文件路径 (CSV)
    """
    
    # 度量名称常量
    METRIC_LOCK = '{ FIXED [lc_small_channel_name],[种子用户]:[主锁单标记]}'
    METRIC_ASSIST = '来源辅助标记'
    
    print(f"读取文件: {input_file}")
    try:
        df = pd.read_csv(input_file, encoding='utf-16', sep='\t')
    except Exception as e:
        print(f"读取文件失败: {e}")
        return

    # --- 0. 预处理：分组归并 ---
    group_file = os.path.join(os.path.dirname(input_file), '直播业务_group_2025.csv')
    if os.path.exists(group_file):
        print(f"读取分组文件: {group_file}")
        try:
            # 尝试读取分组文件
            try:
                group_df = pd.read_csv(group_file)
            except UnicodeDecodeError:
                group_df = pd.read_csv(group_file, encoding='gbk')
            
            if 'lc_small_channel_name' in group_df.columns:
                live_channels = group_df['lc_small_channel_name'].unique().tolist()
                print(f"发现 {len(live_channels)} 个直播业务渠道，将归并为 '直播业务(Group)'")
                
                # 归并 lc_small_channel_name (行渠道)
                mask_source = df['lc_small_channel_name'].isin(live_channels)
                df.loc[mask_source, 'lc_small_channel_name'] = '直播业务(Group)'
                
                # 归并 md5_锁单渠道 (列渠道)
                mask_target = df['md5_锁单渠道'].isin(live_channels)
                df.loc[mask_target, 'md5_锁单渠道'] = '直播业务(Group)'
                
                # 注意：由于归并，原来不同的行现在可能变成了相同的 (channel, target, metric)，需要重新聚合
                # 尤其是锁单数，原来是 FIXED LOD，现在合并了渠道，锁单数应该是这些渠道锁单数的总和吗？
                # 对于 FIXED LOD 表达式，通常是行级别的。
                # 原始数据结构：每行是一个 (源渠道, 目标渠道) 的组合。
                # 锁单数度量 METRIC_LOCK 的值在原始数据中是针对该行渠道的锁单数。
                # 当多个行渠道合并为一个 '直播业务(Group)' 时，我们需要对它们的锁单数求和吗？
                # 是的。逻辑上：A有10个锁单，B有20个锁单。合并后 A+B 应该有 30 个锁单。
                # 但是要注意去重。原始数据中，同一个 lc_small_channel_name 会对应多个 md5_锁单渠道，
                # 但 METRIC_LOCK 的值是针对 lc_small_channel_name 的，所以在同一个 lc_small_channel_name 下是重复的。
                # 我们需要在聚合前先去重处理锁单数。
                
                # 这里的处理逻辑需要非常小心。
                # 建议策略：
                # 1. 先分离出锁单数数据和助攻数数据。
                # 2. 对锁单数数据：先按原始渠道去重（每个渠道取一个值），然后将原始渠道映射到新组名，再按新组名求和。
                # 3. 对助攻数数据：直接映射组名，然后按 (行, 列) 求和。
                
            else:
                print("警告: 分组文件中未找到 'lc_small_channel_name' 列")
        except Exception as e:
            print(f"读取分组文件失败: {e}")
    else:
        print(f"提示: 未找到分组文件 {group_file}，跳过分组步骤")

    # 1. 处理锁单数 (每个行渠道的总锁单数)
    print("处理锁单数...")
    df_lock = df[df['度量名称'] == METRIC_LOCK].copy()
    
    # 注意：如果进行了分组，df_lock 中的 lc_small_channel_name 已经是 '直播业务(Group)' 了。
    # 但是，简单的 drop_duplicates 会导致数据丢失。
    # 例如：原渠道 A (锁单10), 原渠道 B (锁单20)。
    # 替换后：A->Group, B->Group。
    # df_lock 中现在有很多行 Group，值分别是 10, 10, ..., 20, 20, ...
    # 我们不能直接 sum，因为每行是重复的。也不能直接 drop_duplicates，因为 10 和 20 都是有效的。
    
    # 更稳妥的方法：
    # 回到原始 df（未替换前的状态）提取锁单数，处理完后再合并。
    # 为了避免复杂性，我们重新读取一次原始数据用于计算锁单数，或者在替换前备份。
    # 但由于前面已经替换了 df，这里我们需要重新思考逻辑。
    
    # 修正策略：
    # 既然 df 已经被替换了，我们无法区分哪些行属于原来的 A 还是 B。
    # 所以，必须在替换前处理锁单数。
    
    # 让我们回滚一下思路，重写整个处理流程。
    # 重新读取数据
    df = pd.read_csv(input_file, encoding='utf-16', sep='\t')
    
    # 1.1 提取原始锁单数（未分组）
    df_lock_raw = df[df['度量名称'] == METRIC_LOCK].drop_duplicates(subset=['lc_small_channel_name'])[['lc_small_channel_name', '度量值']]
    df_lock_raw = df_lock_raw.rename(columns={'度量值': '锁单数'})
    
    # 1.2 提取原始助攻数（未分组）
    df_assist_raw = df[df['度量名称'] == METRIC_ASSIST].copy()
    
    # --- 分组逻辑应用 ---
    if os.path.exists(group_file):
         try:
            try:
                group_df = pd.read_csv(group_file)
            except UnicodeDecodeError:
                group_df = pd.read_csv(group_file, encoding='gbk')
            
            if 'lc_small_channel_name' in group_df.columns:
                live_channels = set(group_df['lc_small_channel_name'].unique())
                print(f"应用分组: {len(live_channels)} 个渠道 -> '直播业务(Group)'")
                
                # 更新锁单数表
                # 如果渠道在列表中，改名。然后按新名字 groupby sum
                df_lock_raw['lc_small_channel_name'] = df_lock_raw['lc_small_channel_name'].apply(
                    lambda x: '直播业务(Group)' if x in live_channels else x
                )
                df_lock_final = df_lock_raw.groupby('lc_small_channel_name', as_index=False)['锁单数'].sum()
                
                # 更新助攻数表
                # 更新 Source
                df_assist_raw['lc_small_channel_name'] = df_assist_raw['lc_small_channel_name'].apply(
                    lambda x: '直播业务(Group)' if x in live_channels else x
                )
                # 更新 Target
                df_assist_raw['md5_锁单渠道'] = df_assist_raw['md5_锁单渠道'].apply(
                    lambda x: '直播业务(Group)' if x in live_channels else x
                )
                # 重新聚合助攻数
                df_assist_final = df_assist_raw.groupby(['lc_small_channel_name', 'md5_锁单渠道'], as_index=False)['度量值'].sum()
                
            else:
                df_lock_final = df_lock_raw
                df_assist_final = df_assist_raw
         except Exception as e:
            print(f"分组处理出错: {e}")
            df_lock_final = df_lock_raw
            df_assist_final = df_assist_raw
    else:
        df_lock_final = df_lock_raw
        df_assist_final = df_assist_raw

    print(f"处理后锁单数行数: {len(df_lock_final)}")
    
    # 2. 生成透视表
    print("生成助攻矩阵...")
    df_assist_final = df_assist_final.dropna(subset=['md5_锁单渠道'])
    
    if df_assist_final.empty:
        pivot_assist = pd.DataFrame()
    else:
        pivot_assist = df_assist_final.pivot(
            index='lc_small_channel_name',
            columns='md5_锁单渠道',
            values='度量值'
        ).fillna(0)
        pivot_assist.columns = [f"助攻数_{col}" for col in pivot_assist.columns]
    
    # 3. 合并数据
    print("合并最终结果...")
    # 使用锁单数表作为主表（因为它包含了所有行渠道，即使没有助攻）
    # 或者取并集
    all_channels = pd.Index(df_lock_final['lc_small_channel_name'].unique()).union(
        pd.Index(df_assist_final['lc_small_channel_name'].unique()) if not df_assist_final.empty else []
    ).sort_values()
    
    result = pd.DataFrame(index=all_channels)
    result.index.name = 'lc_small_channel_name'
    
    result = result.join(df_lock_final.set_index('lc_small_channel_name'), how='left')
    result['锁单数'] = result['锁单数'].fillna(0)
    
    if not pivot_assist.empty:
        result = result.join(pivot_assist, how='left')
    
    result = result.fillna(0)
    
    # 4. 保存结果
    print(f"保存结果到: {output_file}")
    try:
        result.to_csv(output_file, encoding='utf-8-sig')
        print("完成！")
        print(f"结果预览 (前5行):")
        print(result.head())
    except Exception as e:
        print(f"保存文件失败: {e}")

if __name__ == "__main__":
    # 默认路径配置
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DEFAULT_INPUT = os.path.join(BASE_DIR, "渠道归因（来源矩阵)_data.csv")
    DEFAULT_OUTPUT = os.path.join(BASE_DIR, "Attribution_Step2_Data.csv")
    
    input_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    output_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    
    if not os.path.exists(input_path):
        print(f"错误: 输入文件不存在: {input_path}")
    else:
        process_attribution_matrix(input_path, output_path)
