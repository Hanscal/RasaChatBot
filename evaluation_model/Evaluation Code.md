# Evaluation Dialogue System

## 1. test_story

默认情况下，该命令将对任何名称以**test_**开头的文件中的故事运行测试。还可以使用**--stories**参数提供特定的测试故事文件或目录。可以通过运行以下命令来测试：

```python
rasa test
```

```
rasa test --stories tests/test_stories.yml
```

对话测试只与测试用例一样全面和准确，所以在对助手进行改进的同时，应该继续增加测试用例集。一个很好的经验法则是，你应该让你的测试故事代表真实对话的真实分布。Rasa X使基于真实对话添加测试对话变得容易。

#### 样例

```
rasa test --stories data/stories/chitchat_stories.yml
```

## 2. test_nlu

测试自然语言理解（NLU）模型。一旦你的助手部署到现实世界中，它将处理训练数据中没有看到的消息。为了模拟这种情况，应该始终留出部分数据进行测试。可以使用以下方法将NLU数据拆分为训练集和测试集：

```python
rasa data split nlu
```

接下来，可以使用以下方法查看经过训练的NLU模型对生成的测试集数据的预测效果：

```python
rasa test nlu
    --nlu train_test_split/test_data.yml
```

要更广泛地测试模型，请使用交叉验证，它会自动创建多个训练/测试拆分：**（很慢，很费时间）**

```python
rasa test nlu
    --nlu data/nlu.yml
    --cross-validation
```

#### NLU性能比较

如果对NLU训练数据进行了重大更改（例如，将一个意图拆分为两个意图或添加了大量训练示例），则应进行完整的NLU评估。需要比较NLU模型的性能，而不需要对NLU模型进行更改。

可以通过在交叉验证模式下运行NLU测试来实现这一点：

```python
rasa test nlu --cross-validation
```

还可以在训练集上训练模型，并在测试集上进行测试。如果使用**train-test**集方法，最好使用**rasa data split**（作为CI步骤的一部分）对数据进行洗牌和拆分，而不是使用静态NLU测试集，后者很容易过时。

#### 比较 NLU Pipelines

为了最大限度地利用训练数据，应该在不同的pipeline和不同数量的训练数据上训练和评估的模型。

为此，请将多个配置文件传递给**rasa test**命令：

```python
rasa test nlu --nlu data/nlu.yml
   --config config_1.yml config_2.yml
```

这将执行几个步骤：

1. 从**data/nlu.yml**创建一个全局80%的训练集/20%的测试拆分。

2. 从全局训练拆分中排除一定百分比的数据。

3. 根据剩余的训练数据，为每个配置提供训练模型。

4. 在全局测试拆分中评估每个模型。

在第2步中，使用不同百分比的训练数据重复上述过程，以了解如果增加训练数据量，每个pipeline将如何运行。由于训练不是完全确定的，所以对于每个指定的配置，整个过程重复三次。

绘制了一张图，显示了所有运行中**f1-scores**的平均值和标准差。**f1-scores**图以及所有训练/测试集、训练模型、分类和错误报告将保存到名为**nlu_comparison_results**的文件夹中。

查看**f1-scores**图可以帮助了解NLU模型是否有足够的数据。如果图表显示，当使用所有训练数据时，**f1-scores**仍在提高，则更多数据可能会进一步提高。但是，如果在使用所有训练数据时**f1-scores**已经稳定下来，添加更多数据可能没有帮助。

如果要更改运行次数或排除百分比，可以：

```python
rasa test nlu --nlu data/nlu.yml
  --config config_1.yml config_2.yml
  --runs 4 --percentages 0 25 50 70 90
```

#### 样例

```
rasa data split nlu
rasa test nlu --nlu train_test_split/test_data.yml
rasa test nlu --nlu data/nlu/chitchat_nlu.yml  --config config.yml config2.yml
```

