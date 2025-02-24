import math
from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from clustviz.agglomerative import dist_mat_gen
from collections import Counter, OrderedDict
from copy import deepcopy
import random

from clustviz.utils import dist1, convert_colors, chernoffBounds, flatten_list, cluster_points, \
    COLOR_DICT, CURE_REPS_COLORS, FONTSIZE_BIGGER, annotate_points, build_initial_matrices, draw_rectangle_or_encircle


def point_plot_mod2(
    X: np.ndarray,
    CURE_df: pd.DataFrame,
    reps: list,
    level_txt: float,
    level2_txt: float = None,
    par_index=None,
    u=None,
    u_cl=None,
    initial_ind=None,
    last_reps: dict = None,
    not_sampled=None,
    not_sampled_ind=None,
    n_rep_fin=None,
):
    """
    Scatter-plot of input data points, colored according to the cluster they belong to.
    A rectangle with red borders is displayed around the last merged cluster; representative points
    of last merged cluster are also plotted in red, along with the center of mass, plotted as a
    red cross. The current number of clusters and current distance are also displayed in the right
    upper corner.

    :param X: input data array.
    :param CURE_df: input dataframe built by CURE algorithm, listing the cluster and the x and y
              coordinates of each point.
    :param reps: list of the coordinates of representative points.
    :param level_txt: distance at which current merging occurs displayed in the upper right corner.
    :param level2_txt: incremental distance (not used).
    :param par_index: partial index to take the shuffling of indexes into account.
    :param u: first cluster to be merged.
    :param u_cl: second cluster to be merged.
    :param initial_ind: initial partial index.
    :param last_reps: dictionary of last representative points.
    :param not_sampled: coordinates of points that have not been initially sampled, in the large dataset version.
    :param not_sampled_ind: indexes of not_sampled point_indices.
    :param n_rep_fin: number of representatives to use for each cluster in the final assignment phase in the large
                      dataset version.
    :return: if par_index is not None, returns the new indexes of par_index.
    """
    # diz is used to take the shuffling of data into account, e.g. if the first row doesn't
    # correspond to point 0: this is useful for the large dataset version of CURE, where data points
    # are randomly sampled, but the initial indices are kept to be plotted.
    if par_index is not None:
        diz = dict(zip(par_index, list(range(len(par_index)))))

    _, ax = plt.subplots(figsize=(14, 6))

    # points that still need to be processed are plotted in lime color
    ax.scatter(X[:, 0], X[:, 1], s=300, color="lime", edgecolor="black", zorder=3)

    # drops the totally null columns, so that the number of columns goes to 2*(cardinality of biggest cluster)
    CURE_df = CURE_df.dropna(1, how="all")

    color_dict_rect = convert_colors(COLOR_DICT, alpha=0.3)

    # to speed things up, this splits all points inside the clusters' names, and start gives the starting index
    # that shows where clusters with more than 1 element start (because they are always appended to CURE_df)
    len_ind = [len(i.split("-")) for i in list(CURE_df.index)]
    start = np.min([i for i in range(len(len_ind)) if len_ind[i] > 1])

    # for each cluster, take the single points composing it and plot them in the appropriate color, if
    # necessary taking the labels of par_index into account
    for ind, i in enumerate(range(start, len(CURE_df))):
        points = cluster_points(CURE_df.iloc[i].name)

        if par_index is not None:
            X_clust = [X[diz[p], 0] for p in points]
            Y_clust = [X[diz[p], 1] for p in points]

        else:
            points = [int(i) for i in points]
            X_clust = [X[p, 0] for p in points]
            Y_clust = [X[p, 1] for p in points]

        ax.scatter(X_clust, Y_clust, s=350, color=COLOR_DICT[ind % len(COLOR_DICT)], zorder=3)

    # last merged cluster, so the last element of matrix CURE_df
    points = cluster_points(CURE_df.iloc[-1].name)
    # finding the new center of mass the newly merged cluster
    if par_index is not None:
        points = [diz[p] for p in points]
        com = X[points].mean(axis=0)
    else:
        points = [int(i) for i in points]
        com = X[points].mean(axis=0)

    # plotting the center of mass, marked with an X
    ax.scatter(com[0], com[1], s=400, color="r", marker="X", edgecolor="black", zorder=3)

    # plotting representative points in red
    x_reps = [i[0] for i in reps]
    y_reps = [i[1] for i in reps]
    ax.scatter(x_reps, y_reps, s=360, color="r", edgecolor="black", zorder=3)

    draw_rectangle_or_encircle(X, points, X_clust, Y_clust, ax, ind)

    # adding labels to points in the plot
    if initial_ind is not None:
        labels = initial_ind
    else:
        labels = range(len(X))

    annotate_points(annotations=labels, points=X, ax=ax)

    num_clust = "n° clust: " + str(len(CURE_df))
    min_dist = "min_dist: " + str(round(level_txt, 5))
    dist_incr = "  ---  dist_incr: " + str(round(level2_txt, 5)) if level2_txt is not None else ""

    title = num_clust + " --- " + min_dist + dist_incr

    ax.set_title(title, fontsize=FONTSIZE_BIGGER)

    plt.show()

    # last phase of the large dataset version
    if last_reps is not None:
        xmin, xmax = ax.get_xlim()
        xwidth = xmax - xmin

        assignment_phase_large_cure(X=X, CURE_df=CURE_df, diz=diz, initial_ind=initial_ind,
                                    last_reps=last_reps, not_sampled=not_sampled,
                                    not_sampled_ind=not_sampled_ind, n_rep_fin=n_rep_fin,
                                    xwidth=xwidth)

    # if par_index is not None, diz is updated with the last merged cluster and its keys are returned
    if par_index is not None:
        diz["(" + u + ")-(" + u_cl + ")"] = len(diz)
        list_keys_diz = list(diz.keys())

        return list_keys_diz


def assignment_phase_large_cure(X, CURE_df, diz, initial_ind, last_reps, not_sampled,
                                not_sampled_ind, n_rep_fin, xwidth):
    """
    In the last phase of CURE algorithm variation for large datasets, arrows are
    displayed from every not sampled point to its closest representative point; moreover, representative
    points are surrounded by small circles, to make them more visible. Representative points of different
    clusters are plotted in different nuances of red.

    :param X: input data array.
    :param diz: indexes of data points, to take shuffling into account.
    :param CURE_df: input dataframe built by CURE algorithm, listing the cluster and the x and y
              coordinates of each point.
    :param initial_ind: initial partial index.
    :param last_reps: dictionary of last representative points.
    :param not_sampled: coordinates of points that have not been initially sampled, in the large dataset version.
    :param not_sampled_ind: indexes of not_sampled point_indices.
    :param n_rep_fin: number of representatives to use for each cluster in the final assignment phase in the large
                      dataset version.
    :param xwidth: plot width.
    """

    fig, ax = plt.subplots(figsize=(14, 6))

    # plot all the points in color lime
    ax.scatter(X[:, 0], X[:, 1], s=300, color="lime", edgecolor="black")

    # find the centers of mass of the clusters using the matrix X to find which points belong to
    # which cluster
    coms = []
    for ind, i in enumerate(range(0, len(CURE_df))):
        points = cluster_points(CURE_df.iloc[i].name)
        for p in points:
            ax.scatter(
                X[diz[p], 0],
                X[diz[p], 1],
                s=350,
                color=COLOR_DICT[ind % len(COLOR_DICT)],
            )
        points = [diz[p] for p in points]
        coms.append(X[points].mean(axis=0))

    # flattening the last_reps values
    flat_reps = flatten_list(list(last_reps.values()))

    # plotting the representatives, surrounded by small circles, and the centers of mass, marked with X
    for i in range(len(last_reps)):
        len_rep = len(list(last_reps.values())[i])

        x = [
            list(last_reps.values())[i][j][0]
            for j in range(min(n_rep_fin, len_rep))
        ]
        y = [
            list(last_reps.values())[i][j][1]
            for j in range(min(n_rep_fin, len_rep))
        ]

        ax.scatter(
            x, y, s=400, color=CURE_REPS_COLORS[i % len(CURE_REPS_COLORS)], edgecolor="black"
        )
        ax.scatter(
            coms[i][0],
            coms[i][1],
            s=400,
            color=CURE_REPS_COLORS[i % len(CURE_REPS_COLORS)],
            marker="X",
            edgecolor="black",
        )

        for num in range(min(n_rep_fin, len_rep)):
            ax.add_artist(
                plt.Circle(
                    (x[num], y[num]),
                    xwidth * 0.03,
                    color=CURE_REPS_COLORS[i % len(CURE_REPS_COLORS)],
                    fill=False,
                    linewidth=3,
                    alpha=0.7,
                )
            )

        ax.scatter(
            not_sampled[:, 0],
            not_sampled[:, 1],
            s=400,
            color="lime",
            edgecolor="black",
        )

    # find the closest representative for not sampled points, and draw an arrow connecting the points
    # to its closest representative
    for ns_point in not_sampled:
        dist_int = []
        for el in flat_reps:
            dist_int.append(dist1(ns_point, el))
        ind_min = np.argmin(dist_int)

        ax.arrow(
            ns_point[0],
            ns_point[1],
            flat_reps[ind_min][0] - ns_point[0],
            flat_reps[ind_min][1] - ns_point[1],
            length_includes_head=True,
            head_width=0.03,
            head_length=0.05,
            color="black"
        )

    # plotting the indexes for each point
    annotate_points(annotations=initial_ind, points=X, ax=ax)

    if not_sampled_ind is not None:
        annotate_points(annotations=not_sampled_ind, points=not_sampled, ax=ax)

    plt.show()


def dist_clust_cure(rep_u: list, rep_v: list) -> float:
    """
    Compute the distance of two clusters based on the minimum distance found between the
    representatives of one cluster and the ones of the other.

    :param rep_u: representatives of the first cluster.
    :param rep_v: representatives of the second cluster.
    :return: distance between two clusters.
    """
    rep_u = np.array(rep_u)
    rep_v = np.array(rep_v)
    distances = []
    for i in rep_u:
        for j in rep_v:
            distances.append(dist1(i, j))
    return np.min(distances)


def update_mat_cure(mat: pd.DataFrame, i: int, j: int, rep_new: dict, name: str) -> pd.DataFrame:
    """
    Update distance matrix of CURE, by computing the new distances from the new representatives.

    :param mat: input dataframe built by CURE algorithm, listing the cluster and the x and y
                coordinates of each point.
    :param i: row index of cluster to be merged.
    :param j: column index of cluster to be merged.
    :param rep_new: dictionary of new representatives.
    :param name: string of the form "(" + u + ")-(" + u_cl + ")", containing the new
                 name of the newly merged cluster.
    :return: updated matrix with new distances
    """
    # taking the 2 rows to be updated
    x = mat.loc[i]
    y = mat.loc[j]

    key_lists = list(rep_new.keys())

    # update all distances from the new cluster with new representatives
    vec = []
    for i in range(len(mat)):
        vec.append(dist_clust_cure(rep_new[name], rep_new[key_lists[i]]))

    # adding new row
    mat.loc["(" + x.name + ")-(" + y.name + ")", :] = vec
    # adding new column
    mat["(" + x.name + ")-(" + y.name + ")"] = vec + [np.inf]

    # dropping the old row and the old column
    mat = mat.drop([x.name, y.name], 0)
    mat = mat.drop([x.name, y.name], 1)

    return mat


def sel_rep(clusters: dict, name: str, c: int, alpha: float) -> list:
    """
    Select c representatives of the clusters: first one is the farthest from the centroid,
    the others c-1 are the farthest from the already selected representatives. It doesn't use
    the old representatives, so it is slower than sel_rep_fast.

    :param clusters: dictionary of clusters.
    :param name: name of the cluster we want to select representatives from.
    :param c: number of representatives we want to extract.
    :param alpha: 0<=float<=1, it determines how much the representative points are moved
                 toward the centroid: 0 means they aren't modified, 1 means that all points
                 collapse to the centroid.
    :return: list of representative points.
    """
    # if the cluster has c points or less, just take all of them as representatives and shrink them
    # according to the parameter alpha
    if len(clusters[name]) <= c:

        others = clusters[name]
        com = np.mean(clusters[name], axis=0)

        for i in range(len(others)):
            others[i] = others[i] + alpha * (com - others[i])

        return others

    # if the cluster has more than c points, use the procedure described in the documentation to pick
    # the representative points
    else:

        others = []  # the representatives
        indexes = (
            []
        )  # their indexes, to avoid picking one point multiple times

        points = clusters[name]
        com = np.mean(points, axis=0)

        # compute distances from the centroid
        distances_com = {i: dist1(p, com) for i, p in enumerate(points)}
        index = max(distances_com, key=distances_com.get)

        indexes.append(index)
        others.append(
            np.array(points[index])
        )  # first point is the farthest from the centroid

        # selecting the other c-1 points
        for _ in range(min(c - 1, len(points) - 1)):
            # here we store the distances of the current point from the alredy selected representatives
            partial_distances = {str(i): [] for i in range(len(points))}
            for i, p in enumerate(points):
                if i not in indexes:
                    for other in others:
                        partial_distances[str(i)].append([dist1(p, np.array(other))])
            partial_distances = dict(
                (k, [np.sum(v)]) for k, v in partial_distances.items()
            )
            index2 = max(partial_distances, key=partial_distances.get)
            indexes.append(int(index2))
            # other points are the farthest from the already selected representatives
            others.append(points[int(index2)])

        # perform the shrinking according to the parameter alpha
        for i in range(len(others)):
            others[i] = others[i] + alpha * (com - others[i])

        return others


def sel_rep_fast(prec_reps: list, clusters: dict, name: str, c: int, alpha: float) -> list:
    """
    Select c representatives of the clusters from the previously computed representatives,
    so it is faster than sel_rep.

    :param prec_reps: list of previously computed representatives.
    :param clusters: dictionary of clusters.
    :param name: name of the cluster we want to select representatives from.
    :param c: number of representatives we want to extract.
    :param alpha: 0<=float<=1, it determines how much the representative points are moved
                 toward the centroid: 0 means they aren't modified, 1 means that all points
                 collapse to the centroid.
    :return: list of representative points.
    """
    com = np.mean(clusters[name], axis=0)

    # if the cluster has c points or less, just take all of them as representatives and shrink them
    # according to the parameter alpha
    if len(prec_reps) <= c:

        others = prec_reps
        for i in range(len(others)):
            others[i] = others[i] + alpha * (com - others[i])

        return others

    # if the cluster has more than c points, use the procedure described in the documentation to pick
    # the representative points
    else:

        others = []  # the representatives
        indexes = (
            []
        )  # their indexes, to avoid picking one point multiple times

        points = prec_reps  # use old representatives

        distances_com = {i: dist1(p, com) for i, p in enumerate(points)}
        index = max(distances_com, key=distances_com.get)

        indexes.append(index)
        others.append(np.array(points[index]))  # first point

        # selecting the other c-1 points
        for step in range(min(c - 1, len(points) - 1)):
            # here we store the distances of the current point from the alredy selected representatives
            partial_distances = {str(i): [] for i in range(len(points))}
            for i in range(len(points)):
                if i not in indexes:
                    for other in others:
                        partial_distances[str(i)].append(
                            [dist1(points[i], np.array(other))]
                        )
            partial_distances = dict(
                (k, [np.sum(v)]) for k, v in partial_distances.items()
            )
            index2 = max(partial_distances, key=partial_distances.get)
            indexes.append(int(index2))
            others.append(
                points[int(index2)]
            )  # other points are the farthest from the already selected representatives

        # perform the shrinking according to the parameter alpha
        for i in range(len(others)):
            others[i] = others[i] + alpha * (com - others[i])

        return others


def form_new_cluster(clusters: dict, u: str, u_cl: str) -> list:
    """
    Form a new cluster from the input ones.

    :param clusters: existing clusters.
    :param u: first cluster.
    :param u_cl: second cluster.
    :return: new cluster obtained by merging the first and second cluster.
    """

    if (np.array(clusters[u]).shape == (2,)) and (
        np.array(clusters[u_cl]).shape == (2,)
    ):
        new_cluster = [clusters[u], clusters[u_cl]]
    elif (np.array(clusters[u]).shape != (2,)) and (
        np.array(clusters[u_cl]).shape == (2,)
    ):
        clusters[u].append(clusters[u_cl])
        new_cluster = clusters[u]
    elif (np.array(clusters[u]).shape == (2,)) and (
        np.array(clusters[u_cl]).shape != (2,)
    ):
        clusters[u_cl].append(clusters[u])
        new_cluster = clusters[u_cl]
    else:
        new_cluster = clusters[u] + clusters[u_cl]

    return new_cluster


def cure(
    X: np.ndarray,
    k: int,
    c: int = 3,
    alpha: float = 0.1,
    plotting: bool = True,
    preprocessed_data=None,
    partial_index=None,
    n_rep_finalclust=None,
    not_sampled=None,
    not_sampled_ind=None,
):
    """
    CURE algorithm: hierarchical agglomerative clustering using representatives. The parameters which default to
    None are used for the large dataset variation of CURE.

    :param X: input data array.
    :param k: desired number of clusters.
    :param c: number of representatives for each cluster.
    :param alpha: parameter that regulates the shrinking of representative points toward the centroid.
    :param plotting: if True, plots all intermediate steps.
    :param preprocessed_data: if not None, must be of the form (clusters,representatives,matrix_a,X_dist1), which is used to perform a warm start.
    :param partial_index: if not None, it is used as index of the matrix_a, of cluster points and of representatives.
    :param n_rep_finalclust: the final representative points used to classify the not_sampled points.
    :param not_sampled: points not sampled in the initial phase.
    :param not_sampled_ind: indexes of not_sampled points.
    :return, rep, a): returns the clusters dictionary, the dictionary of representatives, the matrix a
    """
    # starting from raw data
    if preprocessed_data is None:
        # building a dataframe storing the x and y coordinates of input data points
        CURE_df, CURE_df_nonan = build_initial_matrices(X, partial_index)

        # initial clusters
        if partial_index is not None:
            clusters = dict(zip(partial_index, X))
        else:
            clusters = {str(i): np.array(p) for i, p in enumerate(X)}

        # build Xdist
        X_dist = dist_mat_gen(CURE_df_nonan)

        # initialize representatives
        if partial_index is not None:
            rep = {partial_index[i]: [X[int(i)]] for i in range(len(X))}
        else:
            rep = {str(i): [p] for i, p in enumerate(X)}

        # just as placeholder for while loop
        heap = [1] * len(X_dist)

        # store minimum distances between clusters for each iteration
        levels = []

    # use precomputed data
    else:

        clusters = preprocessed_data[0]
        rep = preprocessed_data[1]
        CURE_df = preprocessed_data[2]
        X_dist = preprocessed_data[3]
        heap = [1] * len(X_dist)
        levels = []

    # store original index
    if partial_index is not None:
        initial_index = deepcopy(partial_index)

    # while the desired number of clusters has not been reached
    while len(heap) > k:

        # find minimum value of heap queue, which stores clusters according to the distance from
        # their closest cluster

        list_argmin = list(X_dist.apply(lambda x: np.argmin(x)).values)
        list_min = list(X_dist.min(axis=0).values)
        heap = dict(zip(list(X_dist.index), list_min))
        heap = dict(OrderedDict(sorted(heap.items(), key=lambda kv: kv[1])))
        closest = dict(zip(list(X_dist.index), list_argmin))

        # get minimum keys and delete them from heap and closest dictionaries
        u = min(heap, key=heap.get)
        levels.append(heap[u])
        del heap[u]
        # u_cl = str(closest[u])
        u_cl = X_dist.columns[closest[u]]
        del closest[u]

        new_cluster = form_new_cluster(clusters, u, u_cl)

        # delete old clusters
        del clusters[u]
        del clusters[u_cl]

        # set new name
        name = "(" + u + ")" + "-" + "(" + u_cl + ")"
        clusters[name] = new_cluster

        # update representatives
        rep[name] = sel_rep_fast(rep[u] + rep[u_cl], clusters, name, c, alpha)

        # update distance matrix
        X_dist = update_mat_cure(X_dist, u, u_cl, rep, name)

        # delete old representatives
        del rep[u]
        del rep[u_cl]

        dim1 = int(CURE_df.loc[u].notna().sum())
        # update the matrix a with the new cluster
        CURE_df.loc["(" + u + ")" + "-" + "(" + u_cl + ")", :] = CURE_df.loc[u].fillna(
            0
        ) + CURE_df.loc[u_cl].shift(dim1, fill_value=0)
        CURE_df = CURE_df.drop(u, 0)
        CURE_df = CURE_df.drop(u_cl, 0)

        if plotting is True:

            # in the large dataset version of CURE
            if partial_index is not None:

                # only in last step of large dataset version of CURE
                if (
                    (len(heap) == k)
                    and (not_sampled is not None)
                    and (not_sampled_ind is not None)
                ):

                    # take random representative points from the final representatives
                    final_reps = {
                        k: random.sample(v, min(n_rep_finalclust, len(v)))
                        for k, v in rep.items()
                                  }

                    partial_index = point_plot_mod2(
                        X=X,
                        CURE_df=CURE_df,
                        reps=rep[name],
                        level_txt=levels[-1],
                        par_index=partial_index,
                        u=u,
                        u_cl=u_cl,
                        initial_ind=initial_index,
                        last_reps=final_reps,
                        not_sampled=not_sampled,
                        not_sampled_ind=not_sampled_ind,
                        n_rep_fin=n_rep_finalclust,
                    )

                # in the intermediate steps of the large dataset version
                else:
                    partial_index = point_plot_mod2(
                        X=X,
                        CURE_df=CURE_df,
                        reps=rep[name],
                        level_txt=levels[-1],
                        par_index=partial_index,
                        u=u,
                        u_cl=u_cl,
                        initial_ind=initial_index,
                    )
            else:
                point_plot_mod2(X, CURE_df, rep[name], levels[-1])

    return clusters, rep, CURE_df


def plot_results_cure(clust: dict) -> None:
    """
    Scatter plot of data points, colored according to the cluster they belong to, after performing
    CURE algorithm.

    :param clust: output of CURE algorithm, dictionary of the form cluster_labels+point_indices: coords of points
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    for v in clust.values():
        v = np.array(v)
        if v.ndim > 1:
            ax.scatter(v[:, 0], v[:, 1], s=300)
        else:
            ax.scatter(v[0], v[1], s=300)

    plt.show()


def dist_mat_gen_cure(reps: dict) -> pd.DataFrame:
    """
    Build distance matrix for CURE algorithm, using the dictionary of representatives.

    :param reps: dictionary of representative points, the only ones used to compute distances
                       between clusters.
    :return: distance matrix as dataframe
    """
    distance_matrix = pd.DataFrame()
    ind = list(reps.keys())
    k = 0
    for i in ind:
        for j in ind[k:]:
            if i != j:

                a = reps[i]
                b = reps[j]

                distance_matrix.loc[i, j] = dist_clust_cure(a, b)
                distance_matrix.loc[j, i] = distance_matrix.loc[i, j]
            else:

                distance_matrix.loc[i, j] = np.inf

        k += 1

    distance_matrix = distance_matrix.fillna(np.inf)

    return distance_matrix


def cure_sample_part(
    X: np.ndarray,
    k: int,
    c: int = 3,
    alpha: float = 0.3,
    u_min: Optional[int] = None,
    f: float = 0.3,
    d: float = 0.02,
    p: Optional[int] = None,
    q: Optional[int] = None,
    n_rep_finalclust: Optional[int] = None,
    plotting: bool = True,
):
    """
    CURE algorithm variation for large datasets.
    Partition the sample space into p partitions, each of size len(X)/p, then partially cluster each
    partition until the final number of clusters in each partition reduces to n/(pq). Then run a second
    clustering pass on the n/q partial clusters for all the partitions.

    :param X: input data array.
    :param k: desired number of clusters.
    :param c: number of representatives for each cluster.
    :param alpha: parameter that regulates the shrinking of representative points toward the centroid.
    :param u_min: size of the smallest cluster u.
    :param f: percentage of cluster points (0 <= f <= 1) we would like to have in the sample.
    :param d: (0 <= d <= 1) the probability that the sample contains less than f*|u| points of cluster u is less than d.
    :param p: the number of partitions.
    :param q: the number >1 such that each partition reduces to n/(pq) clusters.
    :param n_rep_finalclust: number of representatives to use in the final assignment phase.
    :param plotting: if True, plots all intermediate steps.
    :return, rep, mat_a): returns the clusters dictionary, the dictionary of representatives, the matrix a.
    """
    if ((p is None) and (q is not None)) or ((q is None) and (p is not None)):
        raise ValueError("p and q must be both specified if not None.")

    # choose the parameters suggested by the paper if the user doesnt provide input parameters
    if u_min is None:
        u_min = round(len(X) / k)

    if n_rep_finalclust is None:
        n_rep_finalclust = c

    _, df_nonan = build_initial_matrices(X)

    # this is done to ensure that the algorithm starts even when input params are bad
    while True:
        print("new f: ", f)
        print("new d: ", d)
        n = math.ceil(chernoffBounds(u_min=u_min, f=f, N=len(X), k=k, d=d))

        if n <= len(df_nonan):
            b_sampled = df_nonan.sample(n, random_state=42)
            break

        else:
            if f >= 0.19:
                f = f - 0.1
            else:
                d = d * 2

    b_notsampled = df_nonan.loc[
        [str(i) for i in range(len(df_nonan)) if str(i) not in b_sampled.index], :
    ]

    # find the best p and q according to the paper
    if (p is None) and (q is None):

        def g(x):
            res = (x[1] - 1) / (x[0] * x[1]) + 1 / (x[1] ** 2)
            return res

        results = {}
        for i in range(2, 15):
            for j in range(2, 15):
                results[(i, j)] = g([i, j])
        p, q = max(results, key=results.get)
        print("p: ", p)
        print("q: ", q)

    if (n / (p * q)) < 2 * k:
        print("n/pq is less than 2k, results could be wrong.")

    if k * d >= 1:
        print("k*d is greater or equal to 1, results could be wrong.")

    # form the partitions
    lin_sp = np.linspace(0, n, p + 1, dtype="int")
    # lin_sp
    b_partitions = []
    for num_p in range(p):
        # try:
        b_partitions.append(b_sampled.iloc[lin_sp[num_p]: lin_sp[num_p + 1]])
        # except:
        # b_partitions.append(b_sampled.iloc[lin_sp[num_p]:])

    k_prov = round(n / (p * q))

    # perform clustering on each partition separately
    partial_clust = []
    partial_rep = []
    partial_CURE_df = []

    for i in range(p):
        print("\n")
        print(i)
        clusters, rep, CURE_df = cure(
            b_partitions[i].values,
            k=k_prov,
            c=c,
            alpha=alpha,
            plotting=plotting,
            partial_index=b_partitions[i].index,
        )
        partial_clust.append(clusters)
        partial_rep.append(rep)
        partial_CURE_df.append(CURE_df)

    # merging all data into single components
    # clusters
    clust_tot = {}
    for d in partial_clust:
        clust_tot.update(d)
    # representatives
    rep_tot = {}
    for d in partial_rep:
        rep_tot.update(d)
    # mat CURE_df
    diz = {i: len(b_partitions[i]) for i in range(p)}
    num_freq = Counter(diz.values()).most_common(1)[0][0]

    bad_ind = [k for k, v in diz.items() if v != num_freq]

    for ind in bad_ind:
        partial_CURE_df[ind]["{0}x".format(diz[ind])] = [np.nan] * k_prov
        partial_CURE_df[ind]["{0}y".format(diz[ind])] = [np.nan] * k_prov

    CURE_df_tot = partial_CURE_df[0].append(partial_CURE_df[1])
    for i in range(1, len(partial_CURE_df) - 1):
        CURE_df_tot = CURE_df_tot.append(partial_CURE_df[i + 1])

    # mat Xdist
    X_dist_tot = dist_mat_gen_cure(rep_tot)

    # final_clustering
    prep_data = [clust_tot, rep_tot, CURE_df_tot, X_dist_tot]
    clusters, rep, CURE_df = cure(
        b_sampled.values,
        k=k,
        c=c,
        alpha=alpha,
        preprocessed_data=prep_data,
        partial_index=b_sampled.index,
        n_rep_finalclust=n_rep_finalclust,
        not_sampled=b_notsampled.values,
        plotting=plotting,
        not_sampled_ind=b_notsampled.index,
    )

    return clusters, rep, CURE_df


def demo_parameters():
    """Four plots showing the effects on the sample size of various parameters."""
    plt.figure(figsize=(12, 10))
    plt.suptitle("Effects on sample size from different parameters")

    def compute_res(u_size, f, N, k, d):
        res = k * (
                f * N
                + N / u_size * np.log(1 / d)
                + N
                / u_size
                * np.sqrt(np.log(1 / d) ** 2 + 2 * f * u_size * np.log(1 / d))
        )
        return res

    ax0 = plt.subplot(2, 2, 1)

    u_size = 6000
    f = 0.20
    N = 20000
    k = 4
    d = np.linspace(0.0000001, 1, 100)
    res = compute_res(u_size, f, N, k, d)
    ax0.set_title("u_min: {0}, f:{1}, k:{2}".format(u_size, f, k))

    plt.axhline(N, color="r")
    plt.plot(d, res)
    plt.xlabel("d")
    plt.ylabel("sample size")

    ax1 = plt.subplot(2, 2, 2)

    u_size = 3000
    f = 0.2
    N = 20000
    d = 0.1
    k = list(range(1, 13))
    ax1.set_title("u_min: {0}, f:{1}, d:{2}".format(u_size, f, d))
    res = [
        compute_res(u_size, f, N, k[i], d)
        for i in range(len(k))
    ]
    plt.axhline(N, color="r")
    plt.plot(k, res)
    plt.xlabel("k")

    ax2 = plt.subplot(2, 2, 3)

    u_size = 5000
    f = np.linspace(0.00001, 1, 100)
    N = 20000
    d = 0.1
    k = 4
    ax2.set_title("u_min: {0}, d:{1}, k:{2}".format(u_size, d, k))
    res = compute_res(u_size, f, N, k, d)
    plt.axhline(N, color="r")
    plt.plot(f, res)
    plt.xlabel("f")
    plt.ylabel("sample size")

    ax3 = plt.subplot(2, 2, 4)

    u_size = np.linspace(200, 10000, 30)
    f = 0.2
    N = 20000
    d = 0.1
    k = 4
    ax3.set_title("f: {0}, d:{1}, k:{2}".format(f, d, k))
    res = compute_res(u_size, f, N, k, d)
    plt.axhline(N, color="r")
    plt.plot(u_size, res)
    plt.xlabel("u_min")

    plt.show()
