%%
%% Copyright (C) 2015 by Asil Kaan Bozcuoglu
%%
%% This program is free software; you can redistribute it and/or modify
%% it under the terms of the GNU General Public License as published by
%% the Free Software Foundation; either version 3 of the License, or
%% (at your option) any later version.
%%
%% This program is distributed in the hope that it will be useful,
%% but WITHOUT ANY WARRANTY; without even the implied warranty of
%% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
%% GNU General Public License for more details.
%%
%% You should have received a copy of the GNU General Public License
%% along with this program.  If not, see <http://www.gnu.org/licenses/>.
%%

:- module(knowrob_plan_summary,
    [
	generate_pdf_summary/1,
      	create_latex_with_semantic_map/0,
	add_robot_poses/2,
	add_plan_trajectory/4	
    ]).

:- use_module(library('semweb/rdf_db')).
:- use_module(library('semweb/rdfs')).
:- use_module(library('owl')).
:- use_module(library('rdfs_computable')).
:- use_module(library('owl_parser')).
:- use_module(library('jpl')).
:- use_module(library('knowrob_mongo')).


:- rdf_db:rdf_register_ns(rdf, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#', [keep(true)]).
:- rdf_db:rdf_register_ns(owl, 'http://www.w3.org/2002/07/owl#', [keep(true)]).
:- rdf_db:rdf_register_ns(knowrob, 'http://knowrob.org/kb/knowrob.owl#', [keep(true)]).
:- rdf_db:rdf_register_ns(xsd, 'http://www.w3.org/2001/XMLSchema#', [keep(true)]).
:- rdf_db:rdf_register_ns(srdl2comp, 'http://ias.cs.tum.edu/kb/srdl2-comp.owl#', [keep(true)]).

generate_pdf_summary(GoalsRequireHighlightPose) :-
	create_latex_with_semantic_map,
	add_robot_poses('/base_link', GoalsRequireHighlightPose),
	task_goal(T, 'DEMO'),
	task_start(T,S),
	task_end(T,E),
	add_plan_trajectory('/base_link',S,E,10).

create_latex_with_semantic_map :-

    findall(
        ObjectDetail,
        (   
	    rdfs_individual_of(W, knowrob:'SummaryFurniture'),
	    rdf_has(W, knowrob:'widthOfObject', Wi),
	    rdf_has(W, knowrob:'heightOfObject', Hi),
	    rdf_has(W, knowrob:'depthOfObject', Di),
	    rdfs_individual_of(S, knowrob:'SemanticMapPerception'),
	    rdf_has(S, knowrob:'objectActedOn', W),
	    rdf_has(S, knowrob:'eventOccursAt', M),
	    rdf_has(M, knowrob:'m13', X),
	    rdf_has(M, knowrob:'m03', Y),
	    rdf_has(M, knowrob:'m01', Or),
	    term_to_atom( W, Na),
            term_to_atom( Wi, Wa),
	    term_to_atom( Hi, Ha),
	    term_to_atom( Di, Da),
	    term_to_atom( X, Xa),
	    term_to_atom( Y, Ya),
	    term_to_atom( Or, Ora),
	    jpl_new( '[Ljava.lang.String;', [Na,Wa,Ha,Da,Xa,Ya,Ora], ObjectDetail)            
        ),
        ObjectDetails
    ),

    jpl_new( '[[Ljava.lang.String;', ObjectDetails, Objects),



    findall(
        WallDetail,
        (   
	    rdfs_individual_of(W, knowrob:'Wall'),
	    rdf_has(W, knowrob:'widthOfObject', Wi),
	    rdfs_individual_of(S, knowrob:'SemanticMapPerception'),
	    rdf_has(S, knowrob:'objectActedOn', W),
	    rdf_has(S, knowrob:'eventOccursAt', M),
	    rdf_has(M, knowrob:'m13', X),
	    rdf_has(M, knowrob:'m03', Y),
	    rdf_has(M, knowrob:'m01', Or),
            term_to_atom( Wi, Wa),
	    term_to_atom( X, Xa),
	    term_to_atom( Y, Ya),
	    term_to_atom( Or, Ora),
	    jpl_new( '[Ljava.lang.String;', [Wa,Xa,Ya,Ora], WallDetail)            
        ),
        WallDetails
    ),
    jpl_new( '[[Ljava.lang.String;', WallDetails, Walls),

    jpl_new('org.knowrob.interfaces.PDF_factory.PDF_factory', [], PDF),
    jpl_call(PDF, 'createLatex', [Objects, Walls], _R).

add_robot_poses(Link, GoalsRequireHighlightPose) :-
    findall(
        PositionDetail,
        (   
	    member(Goal, GoalsRequireHighlightPose),
	    task_goal(T, Goal),
	    task_start(T,S), 
	    belief_at(robot(Link,Loc), S),
	    nth0(7, Loc, X),
	    nth0(3, Loc, Y),
	    %rdf_has(Loc, knowrob:'m13', X),
	    %rdf_has(Loc, knowrob:'m03', Y),
	    term_to_atom( X, Xa),
	    term_to_atom( Y, Ya),
	    jpl_new( '[Ljava.lang.String;', [Xa,Ya], PositionDetail)	            
        ),
        PositionDetails
    ),

    jpl_new( '[[Ljava.lang.String;', PositionDetails, Positions),
    jpl_new('org.knowrob.interfaces.PDF_factory.PDF_factory', [], PDF),
    jpl_call(PDF, 'locateRobotPositions', [Positions], _R).

add_plan_trajectory(Link,S,E,Interval) :-
    jpl_new('org.knowrob.interfaces.PDF_factory.PDF_factory', [], PDF),
    jpl_call(PDF, 'addPlanTrajectory', [Link, S, E, Interval], _R).
