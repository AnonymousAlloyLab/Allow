package dev.allow.canonical;

import edu.mit.csail.sdg.ast.Expr;
import java.util.List;

/** One exact root occurrence paired with the tree produced by the canonical traversal.
     */
record IslandCapture(List<Integer> path, Expr expression, List<Object> tree) { }
