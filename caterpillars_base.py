import networkx as nx
import itertools
from sympy.parsing.sympy_parser import (parse_expr, standard_transformations, implicit_multiplication_application)
from sympy import *
from collections import Counter
import re
from sympy import symbols, expand, collect, sympify

def create_internal_graph(G, i, degree):
  # создание внутреннего контура для i-ой части гусеницы, в которой degree ножек
  # изначально в контуре будет 8 вершин:

    # f'internal_{i}_left_up_upper',
    # f'internal_{i}_left_up_lower',

    # f'internal_{i}_left_down_upper',
    # f'internal_{i}_left_down_lower',

    # f'internal_{i}_right_up_upper',
    # f'internal_{i}_right_up_lower',

    # f'internal_{i}_right_down_upper',
    # f'internal_{i}_right_down_lower',

    # это мы их соединяем по кругу, но без верхнего ребра
    G.add_edges_from([
        (f'internal_{i}_left_up_upper',f'internal_{i}_left_up_lower'),
        (f'internal_{i}_left_up_lower',f'internal_{i}_left_down_upper'),
        (f'internal_{i}_left_down_upper',f'internal_{i}_left_down_lower'),

        (f'internal_{i}_left_down_lower', f'internal_{i}_right_down_lower'),

        (f'internal_{i}_right_down_lower', f'internal_{i}_right_down_upper'),
        (f'internal_{i}_right_down_upper', f'internal_{i}_right_up_lower'),
        (f'internal_{i}_right_up_lower', f'internal_{i}_right_up_upper'),
      ])

    if degree <= 1:
        # замыкаем внутренний контур
        G.add_edge(f'internal_{i}_left_up_upper', f'internal_{i}_right_up_upper')
    else:
        # иначе нужны дополнительные вершины между internal_{i}_left_up_upper и internal_{i}_right_up_upper
        for j in range(degree - 1):
            G.add_node(f'internal_{i}_middle_{j}')
            if j == 0:
            # новую промежуточную вершину прицепляем к имеющемуся контуру
                G.add_edge(f'internal_{i}_left_up_upper', f'internal_{i}_middle_{j}')
            else:
            # иначе прицепляем ее к промежуточной вершине, которую прицепили на прошлой итерации
                G.add_edge(f'internal_{i}_middle_{j - 1}', f'internal_{i}_middle_{j}')
  
        # окончательно закрываем контур, соединяя последнюю промежуточную вершину с контуром с другой стороны
        G.add_edge(f'internal_{i}_middle_{degree - 2}', f'internal_{i}_right_up_upper')
  
  
def create_graph_and_intersections(configuration):
    # на вход подается массив из чисел, например [1, 2, 0]
    G = nx.Graph()
    # это угловые вершины внешнего контура
    G.add_nodes_from([f'external_left_up', f'external_right_up', f'external_right_down', f'external_left_down'])
  
    # сначала вставляем боковые ребра, они меняться не будут
    G.add_edges_from(
      [
        (f'external_left_up',f'external_left_down'),
        (f'external_right_down', f'external_right_up')
      ]
    )
  
    # список 6-ти элементных кортежей, каждый из которых отвечает за одно пересечение
    intersections = []
  
    # вспомогательные вершины, чтобы обрабатывать верхние и нижние пересечения между соседними С0 в изначальном графе
    external_last_left_node_upper = f'external_left_up'
    external_last_left_node_lower = f'external_left_down'
  
    for i in range(len(configuration)):
        degree = configuration[i]
        create_internal_graph(G, i, degree)
    
        # изменение внешнего контура
        # две крайние верхние (левая и правая) вершины для i-ой части гусеницы
        G.add_node(f'external_{i}_temporary_left')
        G.add_node(f'external_{i}_temporary_right')
        G.add_edge(external_last_left_node_upper, f'external_{i}_temporary_left')
    
        # две крайние нижние (левая и правая) вершины для i-ой части гусеницы
        G.add_node(f'external_{i}_temporary_left_down')
        G.add_node(f'external_{i}_temporary_right_down')
        G.add_edge(external_last_left_node_lower, f'external_{i}_temporary_left_down')
    
        # можем сразу их соединить, потому что все ножки смотрят наверх,
        # и между нижними вершинами внешнего контура не будет промежуточных
        G.add_edge(f'external_{i}_temporary_left_down', f'external_{i}_temporary_right_down')
        external_last_left_node_lower = f'external_{i}_temporary_right_down'
    
        if degree == 0:
          # ножек нет, тогда соединяем эти крайние вершины
            G.add_edge(f'external_{i}_temporary_left', f'external_{i}_temporary_right')
        else:
            for j in range(degree):
                # это сама ножка, а вершина с суффиксом empty - эмуляция разрыва в контуре
                G.add_node(f'external_{i}_{j}_left')
                G.add_node(f'external_{i}_{j}_right')
                G.add_node(f'external_{i}_{j}_empty')
        
                # соединяем ножку
                G.add_edges_from([
                  (f'external_{i}_{j}_left',f'external_{i}_{j}_empty'),
                  (f'external_{i}_{j}_empty',f'external_{i}_{j}_right'),
                ])
        
                if j == 0:
                  # случай, если ножка в этой части первая
                    G.add_edge(f'external_{i}_temporary_left', f'external_{i}_{j}_left')
                    # определяем, какие вершины войдут в пересечение для этой ножки
                    local_external_left = f'external_{i}_temporary_left'
                    local_internal_left = f'internal_{i}_left_up_upper'
                else:
                    # если промежуточная или последняя
                    G.add_edge(f'external_middle_{i}_{j - 1}', f'external_{i}_{j}_left')
                    # определяем, какие вершины войдут в пересечение для этой ножки
                    local_external_left = f'external_middle_{i}_{j - 1}'
                    local_internal_left = f'internal_{i}_middle_{j - 1}'
        
                if j == degree - 1:
                    # случай, если ножка в этой части последняя
                    G.add_edge(f'external_{i}_{j}_right', f'external_{i}_temporary_right')
                    # определяем, какие вершины войдут в пересечение для этой ножки
                    local_external_right = f'external_{i}_temporary_right'
                    local_internal_right = f'internal_{i}_right_up_upper'
                else:
                    # если промежуточная или первая
                    G.add_node(f'external_middle_{i}_{j}')
                    G.add_edge(f'external_{i}_{j}_right', f'external_middle_{i}_{j}')
                    # определяем, какие вершины войдут в пересечение для этой ножки
                    local_external_right = f'external_middle_{i}_{j}'
                    local_internal_right = f'internal_{i}_middle_{j}'
          
                # в порядке обхода заносим вершины в пересечение для текущей ножки
                intersections.append((f'external_{i}_{j}_left', f'external_{i}_{j}_right', local_external_right, local_internal_right, local_internal_left, local_external_left))
    
        # теперь крайняя левая вершина во внешнем контуре сверху - это крайняя правая для i-ой части гусеницы
        external_last_left_node_upper = f'external_{i}_temporary_right'
        if i >= 1:
            # верхнее пересечение, образованное соседними частями
            intersections.append((f'internal_{i}_left_up_lower', f'internal_{i - 1}_right_up_lower', f'internal_{i - 1}_right_up_upper', f'external_{i - 1}_temporary_right', f'external_{i}_temporary_left', f'internal_{i}_left_up_upper'))
            # нижнее пересечение, образованное соседними частями
            intersections.append((f'internal_{i - 1}_right_down_upper', f'internal_{i}_left_down_upper', f'internal_{i}_left_down_lower', f'external_{i}_temporary_left_down', f'external_{i - 1}_temporary_right_down', f'internal_{i - 1}_right_down_lower'))
  
    # окончательно замыкаем внешний контур сверху и снизу
    G.add_edge(external_last_left_node_upper, f'external_right_up')
    G.add_edge(external_last_left_node_lower,  f'external_right_down')
  
    # помечаем цветом вершины, которые отвечают за разрыв контура
    color_map = ['red' if 'empty' in node else 'black' for node in G]
  
    options = {
        'node_color': color_map,
        'node_size': 100,
        'width': 1,
    }
  
    # изначальный граф
    # nx.draw(G, **options)
  
    return (G, intersections)

def simplify_expression(expressions):
    # Используем регулярное выражение для извлечения переменных
    variables = list(set(re.findall(r'c_\d+', ' '.join(expressions))))

    # Создаем символы для переменных
    symbols_list = symbols(variables)

    # Преобразуем выражения в символьные выражения sympy
    sympy_expressions = []
    for expression in expressions:
        sympy_expression = sympify(expression.replace('^', '**'))
        sympy_expressions.append(sympy_expression)

    # Суммируем мономы и упрощаем выражение
    result = sum(sympy_expressions)
    result = expand(result)
    result = collect(result, symbols_list)

    return str(result)

def replace_and_remove_stars(input_string):
    # Заменяем все ** на ^
    modified_string = input_string.replace('**', '^')
    # Удаляем все оставшиеся *
    answer_expressions = modified_string.replace('*', '')
    return answer_expressions

# конфигурация гусеницы, которую надо посчитать
#request = []

while True:

    # Ввод строки с числами, разделёнными пробелами
    input_string = input("Введите конфигурацию гусеницы, разделенную пробелами: ")

    # Разбиение строки на части и преобразование в список целых чисел
    request = list(map(int, input_string.split()))

    # так работает преобразование пересечения
    def handle_intersection(up_up_left, up_up_right, up_right, down_right, down_left, up_left):
        G.remove_edge(up_up_left, up_left)
        G.remove_edge(up_up_right, up_right)
        G.remove_edge(down_left, down_right)

        G.add_edge(up_up_left, down_right)
        G.add_edge(up_up_right, down_left)
        G.add_edge(up_left, up_right)

    # получение числа пересечений для заданной конфигурации
    (G, intersections) = create_graph_and_intersections(request)

    # бинарные комбинации для перебора всех вариантов преобразования исходной гусеницы
    combinations = map(''.join, itertools.product('01', repeat=len(intersections)))

    # полученные мономы (всего 2^n)
    expressions = []

    for combination in combinations:
        # важно каждый раз генерировать свежий исходный граф
        (G, intersections) = create_graph_and_intersections(request)

        for i in range(len(intersections)):
            if combination[i] == '1':
                handle_intersection(*intersections[i])

        # считаем знак монома
        odd = sum([1 if node == '1' else 0 for node in list(combination)]) % 2 == 1
        relation = {}

        # тут считаем, какие у нас будут множители в мономе
        components = list(nx.connected_components(G))
        for component in components:
            entries = sum([1 if 'empty' in node else 0 for node in component])
            if entries not in relation:
                relation[entries] = 1
            else:
                relation[entries] += 1

        multipliers = []
        for key in relation:
            if relation[key] == 1:
                multipliers.append(f'(c_{key})')
            else:
                multipliers.append(f'(c_{key}**{relation[key]})')

        # собираем итоговую формулу монома
        expression = '*'.join(multipliers)
        # print(expression)

        # добавляем знак
        if odd:
            expression = f'(-{expression})'
        else:
            expression = f'(+{expression})'

        # отправляем к остальным мономам
        expressions.append(expression)

    # складываем все мономы
    final_expression = ' + '.join(expressions)
    #print('Формула без сокращений:')
    #print(final_expression)

    # сокращаем все, что сокращается
    #transformations = standard_transformations + (implicit_multiplication_application,)
    print()
    print('После сокращений:')
    #print(expand(parse_expr(final_expression, transformations=transformations)))
    simlpe_expression = simplify_expression(expressions)
    ans_expression = replace_and_remove_stars(simlpe_expression)
    print(ans_expression)
    print()